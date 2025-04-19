from decimal import Decimal

import pytest_asyncio

from app.db.models import Status
from app.db.schemas import Events


@pytest_asyncio.fixture(scope="function")
async def event(session) -> Events:
    event_model = Events(
        odds=Decimal(1.5),
        deadline=80,
        status=Status.IN_PROGRESS
    )
    session.add(event_model)
    await session.commit()
    await session.refresh(event_model)
    return event_model