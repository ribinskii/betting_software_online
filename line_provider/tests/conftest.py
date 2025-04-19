import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app.db.db import get_db
from app.db.schemas import Base
from app.main import app
from app.config import settings
from fastapi import FastAPI


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Создание event loop для сессии тестов"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db_setup():
    """Создание и инициализация тестовой БД"""
    engine = create_async_engine(settings.get_test_db_url, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def session(test_db_setup):
    """Создание тестовой сессии для каждого теста"""
    async_session = async_sessionmaker(
        test_db_setup, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture
async def client(session):
    """Создание тестового клиента с подменой зависимости БД"""

    transport = ASGITransport(app=app)

    async def override_get_db():
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest_asyncio.fixture(autouse=True)
async def clean_tables(session):
    """Очищает все таблицы перед каждым тестом"""
    for table in reversed(Base.metadata.sorted_tables):
        await session.execute(table.delete())
    await session.commit()