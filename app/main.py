import asyncio
import contextlib
import httpx
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.routes import slack, homeassistant
from app.config import settings
from app.services.monitoring import run_peer_watch, get_peer_urls, get_verified_peers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("beacon")

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for background tasks."""
    tasks = []
    
    if settings.heartbeat_url and settings.heartbeat_url.strip():
        tasks.append(asyncio.create_task(run_heartbeat()))
    
    if settings.peer_watch_urls or settings.beacon_service_name:
        tasks.append(asyncio.create_task(run_peer_watch()))
    
    yield
    
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

async def run_heartbeat():
    """Background task to ping the heartbeat URL."""
    async with httpx.AsyncClient() as client:
        while True:
            try:
                logger.debug(f"Sending heartbeat to: {settings.heartbeat_url}")
                response = await client.get(settings.heartbeat_url)
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
            await asyncio.sleep(settings.heartbeat_interval)

app = FastAPI(
    title="Beacon Alert Service",
    description="Modular alert distribution service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(slack.router, prefix="/slack", tags=["Slack"])
app.include_router(homeassistant.router, prefix="/homeassistant", tags=["Home Assistant"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Only show external peers that have been identity-verified
    discovered = await get_verified_peers()
    
    status = {
        "instance_name": settings.beacon_instance_name,
        "app": "healthy",
        "modules": {
            "slack": "configured" if settings.slack_bot_token else "missing_credentials",
            "homeassistant": "configured" if (settings.ha_token or settings.ha_webhook_id) else "missing_credentials",
        },
        "heartbeat": "enabled" if (settings.heartbeat_url and settings.heartbeat_url.strip()) else "disabled",
        "peer_watcher": {
            "status": "enabled" if (settings.peer_watch_urls or settings.beacon_service_name) else "disabled",
            "peers_count": len(discovered),
            "discovered_peers": discovered
        }
    }
    return status


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.app_port)
