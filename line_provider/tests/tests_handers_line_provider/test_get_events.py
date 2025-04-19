from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import insert

from app.db.models import EventsModel, Status
from app.db.schemas import Events
from app.main import app
from app.rabbit.rabbit import RabbitMQSessionManager

pytestmark = [pytest.mark.asyncio]

async def test_get_events_empty(client) -> None:
    response = await client.get("/bet_maker/events")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_events_with_data(client: AsyncClient, event: Events) -> None:
    response = await client.get("/bet_maker/events")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == event.id
    assert data[0]["odds"] == event.odds
    assert data[0]["status"] == event.status.value

async def test_delete_events(client: AsyncClient, event: Events) -> None:
    response_delete = await client.delete(f"/bet_maker/event/{event.id}")

    assert response_delete.status_code == 200

    response = await client.get("/bet_maker/events")
    assert response.status_code == 200
    assert response.json() == []

@patch("app.rabbit.rabbit.RabbitMQSessionManager.publish_message")
async def test_update_event_status(rabbit_mock: AsyncMock, client: AsyncClient, event: Events) -> None:
    rabbit_mock.return_value = None
    response_update = await client.patch(
        f"/bet_maker/event/{event.id}/status?new_status={Status.TEAM_ONE_WON.value}"
    )

    assert response_update.status_code == 200

    response = await client.get("/bet_maker/events")
    assert response.status_code == 200

    data = response.json()
    assert data[0]["status"] == Status.TEAM_ONE_WON.value




