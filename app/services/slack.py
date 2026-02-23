import logging
import asyncio
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class SlackService:
    """Service to handle Slack alert distribution logic."""
    def __init__(self):
        self.token = settings.slack_bot_token
        self.channel_id = settings.slack_channel_id

    async def send_alert(self, payload):
        """Logic to send message to Slack via API."""
        if not self.token or not self.channel_id:
            logger.warning("Slack alert requested, but Slack token or channel ID is not configured.")
            return {"status": "error", "message": "Slack not configured", "platform": "slack"}

        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Defensively handle InternalAlerts that may not have all fields
        msg_text = getattr(payload, "message", "No message provided")
        msg_title = getattr(payload, "title", None)
        msg_level = (getattr(payload, "level", "info") or "info").lower()

        level_emojis = {
            "info": ":information_source:",
            "warning": ":warning:",
            "error": ":rotating_light:",
            "debug": ":mag:"
        }
        status_icon = level_emojis.get(msg_level, ":information_source:")

        if msg_title:
            main_content = f"{status_icon} *{msg_title}*\n{msg_text}"
        else:
            main_content = f"{status_icon} {msg_text}"

        data = {
            "channel": self.channel_id,
            "text": f"{status_icon} {msg_title or 'Alert'}: {msg_text}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": main_content
                    }
                }
            ]
        }

        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers, json=data)
                    response.raise_for_status()
                    
                    result = response.json()
                    if not result.get("ok"):
                        error_msg = result.get("error", "unknown_error")
                        logger.error(f"Slack API Error (Attempt {attempt+1}): {error_msg}")
                        if attempt == max_retries - 1:
                            return {"status": "error", "message": error_msg, "platform": "slack"}
                        continue
                    
                    logger.info(f"Slack Alert Sent: {msg_title or 'Info'} - {msg_text[:50]}...")
                    return {"status": "success", "platform": "slack"}

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Slack attempt {attempt + 1} failed, retrying in {retry_delay}s: {e}")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                    
                logger.error(f"Final Slack retry attempt failed: {e}")
                return {"status": "error", "message": str(e), "platform": "slack"}
