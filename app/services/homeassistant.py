import asyncio
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class HomeAssistantService:
    """Service to handle Home Assistant alert distribution logic."""
    def __init__(self):
        self.url = settings.ha_url.rstrip("/") if settings.ha_url else None
        self.token = settings.ha_token
        self.webhook_id = settings.ha_webhook_id
        self.entity = settings.ha_notify_entity

    async def send_alert(self, payload):
        """Logic to send message to Home Assistant via API or Webhook."""
        if not self.url:
            logger.error("HA_URL is not configured")
            return {"status": "error", "message": "HA_URL is not configured", "platform": "homeassistant"}

        if self.webhook_id:
            return await self._send_via_webhook(payload)
        return await self._send_via_api(payload)

    async def _send_via_webhook(self, payload):
        """Send notification via HA Webhook trigger."""
        url = f"{self.url}/api/webhook/{self.webhook_id}"
        data = {
            "title": payload.title or "Beacon Alert",
            "message": payload.message or "Empty Beacon Message",
            "target": payload.target
        }
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=data)
                    response.raise_for_status()
                    logger.info("HA Webhook alert sent successfully")
                    return {"status": "success", "platform": "homeassistant", "method": "webhook"}
                if attempt < max_retries - 1:
                    logger.warning(f"HA Webhook attempt {attempt + 1} failed, retrying in {retry_delay}s: {e}")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                logger.error(f"Final HA Webhook retry failed: {e}")
                return {"status": "error", "message": str(e), "platform": "homeassistant"}

    async def _send_via_api(self, payload):
        """Send notification via HA REST API."""
        if not self.token:
            logger.error("HA_TOKEN is not configured for API delivery")
            return {"status": "error", "message": "HA_TOKEN is not configured", "platform": "homeassistant"}

        url = f"{self.url}/api/services/notify/{self.entity}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        data = {
            "title": payload.title or "Beacon Alert",
            "message": payload.message or "Empty Beacon Message"
        }
        
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers, json=data)
                    response.raise_for_status()
                    logger.info(f"HA API alert sent to {self.entity}")
                    return {"status": "success", "platform": "homeassistant", "method": "api"}
                if attempt < max_retries - 1:
                    logger.warning(f"HA API attempt {attempt + 1} failed, retrying in {retry_delay}s: {e}")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                
                logger.error(f"Final HA API retry failed: {e}")
                return {"status": "error", "message": str(e), "platform": "homeassistant"}
