from fastapi import APIRouter

from app.api.handlers_line_provider import router_line_provider

router_base = APIRouter()

router_base.include_router(router_line_provider, prefix="/bet_maker")