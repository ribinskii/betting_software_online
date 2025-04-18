import logging

from app.db.models import EventsModel, Status
from app.db.schemas import Events
from app.db.db import get_db
from fastapi import Depends, FastAPI, HTTPException, APIRouter
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.rebbit.rebbit import RabbitMQSessionManager

logger = logging.getLogger(__name__)

router_line_provider = APIRouter()

@router_line_provider.get("/events")
async def get_events(session: AsyncSession = Depends(get_db)):
    query = select(Events)
    result = await session.execute(query)
    events = result.scalars().all()
    print(events)
    return events

@router_line_provider.post("/event")
async def create_event(event: EventsModel=Depends(), session: AsyncSession = Depends(get_db)):
    new_event = Events(
        odds=event.odds,
        deadline=event.deadline,
        status=event.status,
    )
    session.add(new_event)
    await session.commit()
    await session.refresh(new_event)
    return new_event

@router_line_provider.delete("/event/{event_id}")
async def delete_event(event_id: int, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Events).where(Events.id == event_id))
    event = result.scalar_one_or_none()

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    await session.delete(event)
    await session.commit()

    return {"detail": f"Event with id {event_id} deleted successfully"}

@router_line_provider.patch("/event/{event_id}/status")
async def update_event_status(
        event_id: int,
        new_status: Status,
        session: AsyncSession = Depends(get_db),
        rabbitmq: RabbitMQSessionManager = Depends(RabbitMQSessionManager)
):
    try:
        result = await session.execute(select(Events).where(Events.id == event_id))
        event = result.scalar_one_or_none()

        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")

        await session.execute(
            update(Events)
            .where(Events.id == event_id)
            .values(status=new_status)
        )
        await session.commit()

        await rabbitmq.publish_message(
            queue_name="event_status_update_queue",
            message={
                "event_id": event_id,
                "new_status": new_status.value
            }
        )

        return {"message": "Status updated successfully", "event_id": event_id, "new_status": new_status.value}

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating event status: {str(e)}")
