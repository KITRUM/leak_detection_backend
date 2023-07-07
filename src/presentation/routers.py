from fastapi import APIRouter

platforms = APIRouter(prefix="/platforms", tags=["Platforms"])
templates = APIRouter(prefix="/templates", tags=["Templates"])
sensors = APIRouter(prefix="/sensors", tags=["Sensors"])
events = APIRouter(prefix="/events", tags=["Events"])
