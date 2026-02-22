from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.services.homeassistant import HomeAssistantService

router = APIRouter()


class AlertPayload(BaseModel):
    """Pydantic model for incoming Home Assistant alert requests."""
    title: str | None = Field(None, description="Notification title")
    message: str = Field(..., description="Notification text")
    target: str | None = Field(None, description="Notification target")


@router.post("/alert", summary="Send Notification to Home Assistant")
async def send_ha_alert(
    payload: AlertPayload,
    service: HomeAssistantService = Depends(HomeAssistantService),
):
    """
    Endpoint to send an alert to Home Assistant.

    **Required Body Fields:**
    - `message`: (str) The content for the notification.

    **Optional Body Fields:**
    - `title`: (str) Header for the notification.
    - `target`: (str) Specific device ID or notify service target. null or leave it out
    """
    return await service.send_alert(payload)
