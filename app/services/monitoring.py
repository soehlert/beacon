import asyncio
import socket
import logging
import httpx
from pydantic import BaseModel
from app.config import settings
from app.services.slack import SlackService
from app.services.homeassistant import HomeAssistantService

logger = logging.getLogger(__name__)

# Global cache to avoid repetitive socket/DNS lookups
_cached_local_ip = None


class InternalAlert(BaseModel):
    """Simple model to satisfy the service.send_alert interface."""
    title: str | None = "Beacon Peer Watcher"
    message: str
    target: str | None = None


async def get_peer_urls():
    """Discover peer URLs via config or Docker DNS."""
    # Point out we're using the global var, not some local var
    global _cached_local_ip
    urls = set()
    
    # Manual URLs from config
    for url in settings.peer_watch_urls:
        urls.add(url.rstrip("/"))

    # Automatic Docker DNS discovery
    try:
        # This will return all replica IPs for the service name in a Docker network
        # e.g., 'beacon' -> ['172.18.0.2', '172.18.0.3']
        infos = socket.getaddrinfo(settings.beacon_service_name, settings.app_port)
        for info in infos:
            ip = info[4][0]
            # Wrap IPv6 addresses in brackets for valid URL formatting
            if ":" in ip:
                ip = f"[{ip}]"
            urls.add(f"http://{ip}:{settings.app_port}")
    except socket.gaierror:
        # Not in a Docker network or service name not found
        pass

    # Don't monitor ourselves
    if _cached_local_ip is None:
        try:
            # Get the primary local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((settings.local_ip_discovery_host, 80))
            _cached_local_ip = s.getsockname()[0]
            s.close()
            logger.debug(f"Discovered local IP for exclusion: {_cached_local_ip}")
        except Exception as e:
            logger.warning(f"Could not discover local IP: {e}")

    final_urls = []
    self_url = settings.beacon_instance_url.rstrip("/") if settings.beacon_instance_url else None
    
    for url in urls:
        if self_url and url == self_url:
            continue
        if _cached_local_ip and f"://{_cached_local_ip}:" in url:
            continue
        final_urls.append(url)
    
    return final_urls

async def run_peer_watch():
    """Background task to monitor peer Beacon instances."""
    # Tracking state of peers to ensure we only send one alert per status change.
    # down_alert_sent[url] = True means the peer is currently down and we've already notified the user.
    down_alert_sent = {}
    
    slack = SlackService()
    ha = HomeAssistantService()

    iteration = 0
    peer_urls = []

    # Startup grace period to allow network/peers to stabilize
    await asyncio.sleep(10)

    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            # Re-discover peers every 10 iterations
            if iteration % 10 == 0:
                peer_urls = await get_peer_urls()
            
            for url in peer_urls:
                # Initialize state for any newly discovered peers
                if url not in down_alert_sent:
                    down_alert_sent[url] = False

                try:
                    response = await client.get(url + "/health")
                    is_healthy = response.status_code == 200
                except Exception:
                    is_healthy = False

                # Peer just went down
                if not is_healthy and not down_alert_sent[url]:
                    msg = f"CRITICAL: Peer Beacon instance at {url} is UNREACHABLE."
                    logger.critical(msg)
                    alert = InternalAlert(message=msg)
                    
                    if settings.slack_bot_token:
                        await slack.send_alert(alert)
                    if settings.ha_url:
                        await ha.send_alert(alert)
                    
                    down_alert_sent[url] = True

                # Peer was down, but is now healthy again
                elif is_healthy and down_alert_sent[url]:
                    msg = f"RESOLVED: Peer Beacon instance at {url} is back online."
                    logger.info(msg)
                    alert = InternalAlert(message=msg)
                    
                    if settings.slack_bot_token:
                        await slack.send_alert(alert)
                    if settings.ha_url:
                        await ha.send_alert(alert)
                    
                    down_alert_sent[url] = False

            iteration += 1
            await asyncio.sleep(settings.peer_watch_interval)
