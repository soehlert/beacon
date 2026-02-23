# Project Beacon

Project Beacon is a notification broker designed to centralize alerting across multiple platforms through a single API. It allows infrastructure components to send alerts using a consistent JSON payload, regardless of the destination.

## Functionality

- **Centralized Alerting**: Send a single request to Beacon to distribute notifications to various platforms.
- **Modular Architecture**: The service is structured to support the addition of new notification providers.
- **Standardized Schema**: Uses a consistent data structure for all endpoints, simplifying integration for external scripts and services.
- **Infrastructure Peer Watcher**: Automatically discovers and monitors other Beacon instances in the network to ensure high availability.
- **FastAPI Backend**: Built with FastAPI and containerized for consistent deployment.

## Supported Modules

- **Slack**: Delivery to channels via Bot OAuth tokens.
- **Home Assistant**: Support for mobile app notifications and persistent phone alerts via Webhooks or REST API.

## Usage

The service includes an interactive API playground (Swagger UI) at:

`http://<server-ip>:7867/docs`

### Example Requests

#### 1. Slack Alert
```json
POST /slack/alert
{
  "title": "Infrastructure Alert",
  "message": "Backup job 'daily_sync' completed successfully.",
  "level": "info"
}
```

#### 2. Home Assistant API (Direct Notification)
```json
POST /homeassistant/alert
{
  "title": "System Monitor",
  "message": "Server 'nas-01' temperature is high (65°C)."
}
```

#### 3. Home Assistant Webhook (Targeted)
```json
POST /homeassistant/alert
{
  "title": "Security Alert",
  "message": "Motion detected in the garage.",
  "target": "family_phones"
}
```

## Configuration

Detailed configuration steps for Slack and Home Assistant are located in the [Setup Guide](docs/setup.md).
