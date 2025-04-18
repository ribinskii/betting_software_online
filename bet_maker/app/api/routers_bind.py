from fastapi import APIRouter

from app.api.handlers_bet_maker import router_bet_maker

router_base = APIRouter()

router_base.include_router(router_bet_maker, prefix="/bet_maker")