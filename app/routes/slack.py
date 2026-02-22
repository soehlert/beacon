from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.services.slack import SlackService

router = APIRouter()


class AlertPayload(BaseModel):
    """Pydantic model for incoming Slack alert requests."""
    title: str | None = Field(None, description="Alert title")
    message: str = Field(..., description="Message text")
    level: str = Field("info", description="Alert level")


@router.post("/alert", summary="Send Alert to Slack")
async def send_slack_alert(
    payload: AlertPayload,
    service: SlackService = Depends(SlackService),
):
    """
    Endpoint to send an alert to a Slack channel.

    **Required Body Fields:**
    - `message`: (str) The main text to send.

    **Optional Body Fields:**
    - `title`: (str) Bold heading at the top.
    - `level`: (str) Severity: info (default), warning, error.
    """
    return await service.send_alert(payload)
