from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using Pydantic Settings."""
    # Slack Configuration
    slack_bot_token: str | None = None
    slack_channel_id: str | None = None

    # Home Assistant Configuration
    ha_url: str | None = None
    ha_token: str | None = None
    ha_webhook_id: str | None = None
    ha_notify_entity: str = "notify"

    # App Settings
    app_port: int = 7867
    debug: bool = False
    heartbeat_url: str | None = None
    heartbeat_interval: int = 900
    
    # Peer Monitoring (Watcher) - Infrastructure health checks
    peer_watch_urls: list[str] = []
    peer_watch_interval: int = 300
    beacon_instance_name: str = "beacon"
    beacon_instance_url: str | None = None
    beacon_service_name: str = "beacon"
    local_ip_discovery_host: str = "8.8.8.8"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
