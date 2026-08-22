# Endurain Integration

[Endurain](https://docs.endurain.com/) is a self-hosted fitness tracking platform. Integrating Endurain with AdventureLog lets you browse activities from your instance and import GPX tracks into visits, similar to the Strava integration.

## Setup

1. Ensure your Endurain instance is reachable from the AdventureLog **backend** (not just your browser). Avoid `localhost` or `127.0.0.1` if AdventureLog runs in Docker on another host.
2. Open **Settings → Integrations** in AdventureLog.
3. Enter your Endurain server URL (e.g. `https://endurain.example.com`).
4. Enter your Endurain username and password, then click **Connect with password**.
5. If MFA is enabled on your Endurain account, enter your TOTP or backup code when prompted.

AdventureLog stores JWT access and refresh tokens on the server. Tokens are never returned to the browser after connection.

AdventureLog uses Endurain's mobile client authentication flow server-side so refresh tokens are available for long-lived API access.

## Importing activities into visits

1. Open a location and add or edit a visit with dates.
2. Click the **Endurain activities** button on the visit.
3. Click the import button on an activity. AdventureLog fetches the GPX from Endurain automatically and attaches it to the visit.

Unlike Strava, you do not need to manually download and re-upload GPX files. AdventureLog generates GPX from Endurain GPS streams server-side when you import an activity.

## Token refresh and reconnection

Access tokens expire after about 15 minutes. AdventureLog refreshes them automatically using the stored refresh token.

If refresh fails (revoked session, token reuse detection, etc.), disconnect and reconnect Endurain in Settings.

## Security notes

- Use HTTPS for your Endurain server in production.
- JWT tokens are stored on the AdventureLog server per user.
- API keys cannot be used for reading activities in Endurain; JWT is required for `activities:read`.

For authentication details, see the [Endurain developer authentication guide](https://docs.endurain.com/developer-guide/authentication/).
