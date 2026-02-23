# Setup Guide: Project Beacon

This document provides instructions for setting up the external services required by Beacon.

## Slack Setup

To enable Slack alerts, you need to create a Slack App and obtain an OAuth token.

### 1. Create a Slack App
1. Go to [api.slack.com/apps](https://api.slack.com/apps).
2. Click **Create New App** -> **From scratch**.
3. **App Name**: "Beacon" (or your choice).
4. **Workspace**: Select the workspace you own.

### 2. Set App Icon (Recommended)
1. In the sidebar, select **Basic Information**.
2. Scroll to **Display Information**.
3. **App Icon**: Upload an icon (e.g., the Project Beacon lighthouse icon).

### 3. Configure Permissions (Scopes)
1. In the sidebar, select **OAuth & Permissions**.
2. Scroll to **Scopes** -> **Bot Token Scopes**.
3. Add the `chat:write` scope.
4. (Optional) Add `chat:write.public` if you want the bot to post in public channels without being invited.

### 4. Install & Get Token
1. Scroll back up and click **Install to Workspace**.
2. Click **Allow**.
3. Copy the **Bot User OAuth Token** (starts with `xoxb-`).
4. Paste this into your `.env` file as `SLACK_BOT_TOKEN`.

### 5. Get Channel ID
1. In Slack, right-click the channel you want to send alerts to.
2. Select **View channel details**.
3. The **Channel ID** is at the bottom (starts with `C`).
4. Paste this into your `.env` file as `SLACK_CHANNEL_ID`.
5. **Crucial**: If you didn't add `chat:write.public`, you MUST invite the bot to the channel: `/invite @Beacon`.

---

## Home Assistant Setup

### 1. Common Configuration
Before choosing a delivery method, ensure your base URL is set.
- **Set URL**: Your `HA_URL` in `.env` should be the base URL of your HA instance (e.g., `https://hass.soehlert.com`).

#### Targeted Notifications (HA_NOTIFY_ENTITY)
By default, Beacon calls the generic `notify.notify` service. You can target specific devices or groups by setting `HA_NOTIFY_ENTITY`.

**Exact `.env` examples:**
- **Specific Phone**: `HA_NOTIFY_ENTITY=mobile_app_pixel_9`
- **Family Group**: `HA_NOTIFY_ENTITY=all_devices`
- **Room Notifications**: `HA_NOTIFY_ENTITY=living_room_tv`
- **Admin Alerts**: `HA_NOTIFY_ENTITY=persistent_notification`

---

### 2. Method A: Webhook Integration (Recommended)
Webhooks are the preferred way to integrate with Home Assistant for several reasons:
- **Security**: No Long-Lived Access Tokens are required in the `.env` file.
- **Decoupling**: You define the logic (who to notify, what sounds to play) in Home Assistant, not in Beacon.
- **Flexibility**: Easily handle different "targets" (e.g., different family members) using HA's automation engine.

#### Configuration Steps:
2. **Trigger**: Select **Webhook**. Set a **Webhook ID** (e.g., `beacon_alert`).
3. **Action**: Search for **Notifications: Send a notification**.
4. **Configuration**: Switch to the **YAML Editor** (click the three dots) and use this block to support titles, messages, and persistent tags:
   ```yaml
   action: notify.mobile_app_your_phone
   data:
     title: "{{ trigger.json.title | default('Beacon Alert') }}"
     message: "{{ trigger.json.message }}"
     target: "{{ trigger.json.target | default('') }}"
     data:
       tag: "beacon-alert"
       persistent: true
       sticky: true
   ```
5. Add `HA_WEBHOOK_ID=beacon_alert` to your `.env`.

---

### 3. Method B: REST API Integration
If you prefer direct service calls without an automation:

1. **Get Long-Lived Access Token**:
   - In Home Assistant, click your profile name (bottom left).
   - Scroll to the bottom to **Long-Lived Access Tokens**.
   - Click **Create Token**, name it "Beacon", and copy the token.
   - Paste this into your `.env` file as `HA_TOKEN`.

---

### 4. Usage Notes
- **The `target` field**: In the Beacon API, this maps directly to the `target` parameter in Home Assistant's `notify` services.
    - For example, if you use a generic `notify.notify` service, you can pass a specific device ID or platform to the `target` field in the Beacon request to limit where the notification goes.
    - In Webhook mode, you must explicitly use `{{ trigger.json.target }}` in your HA automation's YAML/Visual configuration to make use of it (as shown in the YAML example above).

---

## Example API Payloads

You can send alerts to Beacon via `POST` requests. These endpoints are how other services trigger notifications through Beacon.

### Slack Alert (`POST /slack/alert`)
```json
{
  "title": "Server Status",
  "message": "Storage usage exceeded 90% on 'media-server'.",
  "level": "error"
}
```

### Home Assistant Alert (`POST /homeassistant/alert`)
```json
{
  "title": "Home Security",
  "message": "Front door opened while in Away mode.",
  "target": "mobile_app_pixel_9"
}
```

---

## Monitoring & Heartbeat

### Heartbeat (External Check-in)
Beacon can automatically "check in" with an external monitoring service to ensure it is online.

1. In Uptime Robot, create a new monitor.
2. Select **Monitor Type**: **Heartbeat (Push)**.
3. Set your preferred interval (e.g., 15 minutes).
4. Copy the unique **Heartbeat ID** or the full URL.
5. Set `HEARTBEAT_URL` in `.env` to the unique URL provided.
6. Set `HEARTBEAT_INTERVAL` in `.env` (e.g., `900` for 15 minutes).

### Peer Watcher (Internal Discovery)
If running multiple instances, Beacon discovers peers via Docker DNS or `PEER_WATCH_URLS`.

## Environment Variables Reference & Optional Settings

Beacon is built to be resilient. You can run the application with minimal configuration, and unconfigured modules will simply gracefully skip or return an error without crashing the application.

### Disabling Modules

You can disable specific modules by commenting out their variables or explicitly leaving them blank.

1. **Slack (`SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`)**
   - **If blank**: Any incoming `POST /slack/alert` requests will be gracefully rejected with a "Slack not configured" message. Beacon will not crash.
2. **Home Assistant (`HA_URL`, `HA_TOKEN`, `HA_WEBHOOK_ID`)**
   - **If blank**: Home Assistant integration is disabled. Incoming requests will fail gracefully.
3. **Heartbeat Monitoring (`HEARTBEAT_URL`)**
   - **If blank**: Beacon will skip initializing the background heartbeat task. It will not ping external services (like uptimerobot) on a schedule. You can set it to `HEARTBEAT_URL=` in `.env`.
4. **Peer Monitoring (`PEER_WATCH_URLS`, `BEACON_SERVICE_NAME`)**
   - **If both are blank**: Beacon will not monitor external peer instances and will not query Docker DNS for internal replicas. The peer watcher background task will be disabled entirely.
   - **`BEACON_SERVICE_NAME`**: Defaults to `beacon`. If left blank (`BEACON_SERVICE_NAME=`), Beacon will skip querying Docker's internal DNS resolver to automatically find swarm/compose siblings.
   - **How to pass a blank list**: Because Beacon uses strict JSON-based parsing for lists, you **must** use valid JSON array syntax to pass an empty list if you choose to define it:
     ```env
     PEER_WATCH_URLS='[]'
     ```
     Alternatively, you can safely completely delete or comment out the line in the `.env` file, and Beacon will default to an empty list `[]` automatically.
5. **Peer Filtering (`BEACON_INSTANCE_URL`, `LOCAL_IP_DISCOVERY_HOST`)**
   - These are optional helper variables used by the Peer Watcher to prevent Beacon from accidentally "monitoring" itself when scaling horizontally.
   - **If `BEACON_INSTANCE_URL` is blank**: Beacon will attempt to automatically discover its own IP using the `LOCAL_IP_DISCOVERY_HOST` (default `8.8.8.8`) and aggressively filter itself out of the aggregated peer list so it doesn't alert if it goes down.
   - **If `LOCAL_IP_DISCOVERY_HOST` is blank**: Beacon will skip the automatic IP lookup fallback.

---

## High Availability & Scaling

Beacon is designed to be stateless and can be scaled horizontally behind a reverse proxy like **Traefik**.

### 1. Redundancy
If you use a container orchestrator (like Portainer or Docker Swarm), you can set the **replicas** to 2 or more. Traefik will automatically discover all instances and load-balance requests between them.

### 2. Monitoring the "Watchers"
By using the Heartbeat monitoring above, you ensure that if your entire server or cluster goes down, the external monitoring service will notify you, even if Beacon's internal alert paths are unreachable.
