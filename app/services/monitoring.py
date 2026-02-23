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
# Global to track peers that have been verified as NOT ourselves
_verified_peers = set()
# Global to track URLs that have been identified as ourselves
_known_self_urls = set()


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
        # Force IPv4 only (AF_INET) for peer discovery to ensure reliability
        infos = socket.getaddrinfo(settings.beacon_service_name, settings.app_port, family=socket.AF_INET)
        for info in infos:
            ip = info[4][0]
            urls.add(f"http://{ip}:{settings.app_port}")
    except socket.gaierror:
        # Not in a Docker network or service name not found
        pass

    return list(urls)


async def get_verified_peers():
    """Return the list of peers verified as external instances."""
    return list(_verified_peers)

async def run_peer_watch():
    """Background task to monitor peer Beacon instances."""
    # Tracking state of peers to ensure we only send one alert per status change.
    down_alert_sent = {}
    
    slack = SlackService()
    ha = HomeAssistantService()

    logger.info("Peer Watcher: Starting in 30 seconds to allow network stabilization...")
    await asyncio.sleep(30)
    logger.info("Peer Watcher: Starting monitoring loop.")

    iteration = 0
    peer_urls = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            current_pass_verified = set()
            # Re-discover peers every 10 iterations
            if iteration % 10 == 0:
                peer_urls = await get_peer_urls()
            
            for url in peer_urls:
                # 1. Skip if we already confirmed this URL is US
                if url in _known_self_urls:
                    continue

                # Initialize state for any newly discovered peers
                if url not in down_alert_sent:
                    down_alert_sent[url] = False

                try:
                    response = await client.get(url + "/health")
                    response.raise_for_status()
                    data = response.json()
                    
                    # Identity-based self-exclusion: If the peer is US, skip monitoring it
                    peer_name = data.get("instance_name")
                    if peer_name == settings.beacon_instance_name:
                        logger.debug(f"Peer Watcher: Identified {url} as SELF. Caching and skipping.")
                        _known_self_urls.add(url)
                        continue
                    
                    # If we reach here, it's a legitimate external peer
                    current_pass_verified.add(url)
                    is_healthy = True
                except Exception as e:
                    logger.debug(f"Peer Watcher: Health check failed for {url}: {e}")
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
            
            # Update the global verified list after each pass
            global _verified_peers
            _verified_peers = current_pass_verified
            
            await asyncio.sleep(settings.peer_watch_interval)
