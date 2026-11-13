# Integrations

AdventureLog connects to the services you already run or use. Each one is optional and is set up either by the server administrator or by each user in **Settings**.

## Photos

<div class="al-cards">
  <a class="al-card" href="./immich_integration">
    <strong>Immich</strong>
    <span>Pick photos from your self-hosted Immich library for any location, and open a location's spot on your Immich map.</span>
    <em>Set up by each user</em>
  </a>
</div>

## Activities and trails

<div class="al-cards">
  <a class="al-card" href="./strava_integration">
    <strong>Strava</strong>
    <span>Import your Strava activities into visits, with GPX tracks, distance, and elevation.</span>
    <em>Needs a Strava API application</em>
  </a>
  <a class="al-card" href="./endurain_integration">
    <strong>Endurain</strong>
    <span>Browse activities from a self-hosted Endurain instance and import their GPX tracks into visits.</span>
    <em>Set up by each user</em>
  </a>
  <a class="al-card" href="./wanderer_integration">
    <strong>Wanderer</strong>
    <span>Link trails from a self-hosted Wanderer trail database to your locations, with distance and elevation.</span>
    <em>Set up by each user</em>
  </a>
</div>

## Maps and places

<div class="al-cards">
  <a class="al-card" href="./google_maps_integration">
    <strong>Google Maps</strong>
    <span>Use Google Maps for place search and geocoding in place of OpenStreetMap.</span>
    <em>Needs a Google Maps API key</em>
  </a>
  <a class="al-card" href="./environment_variables#integrations">
    <strong>CARTO basemaps</strong>
    <span>Add more map styles, including a 3D terrain view, with a free CARTO key.</span>
    <em>One environment variable</em>
  </a>
</div>

## Sign-in

<div class="al-cards">
  <a class="al-card" href="./social_auth/oidc">
    <strong>OpenID Connect</strong>
    <span>Sign in through any OIDC provider for single sign-on across your self-hosted apps.</span>
    <em>Set up in the admin panel</em>
  </a>
  <a class="al-card" href="./social_auth/authentik">
    <strong>Authentik</strong>
    <span>Step-by-step setup for Authentik as the identity provider.</span>
    <em>OIDC</em>
  </a>
  <a class="al-card" href="./social_auth/pocket_id">
    <strong>Pocket ID</strong>
    <span>Step-by-step setup for Pocket ID as the identity provider.</span>
    <em>OIDC</em>
  </a>
  <a class="al-card" href="https://www.authelia.com/integration/openid-connect/adventure-log/" target="_blank" rel="noopener noreferrer">
    <strong>Authelia</strong>
    <span>Authelia maintains its own guide for connecting AdventureLog.</span>
    <em>OIDC, external guide</em>
  </a>
  <a class="al-card" href="./social_auth/github">
    <strong>GitHub</strong>
    <span>Let people sign in with their GitHub account.</span>
    <em>OAuth</em>
  </a>
</div>

See [Social Auth & OIDC](social_auth.md) for how sign-in providers work in general.

## Storage, email, and automation

<div class="al-cards">
  <a class="al-card" href="./s3_storage">
    <strong>S3 storage</strong>
    <span>Keep photos and files on AWS S3, Cloudflare R2, MinIO, or DigitalOcean Spaces.</span>
    <em>Environment variables</em>
  </a>
  <a class="al-card" href="./email">
    <strong>SMTP email</strong>
    <span>Send verification, password reset, and mention emails through your mail server.</span>
    <em>Environment variables</em>
  </a>
  <a class="al-card" href="./api_keys">
    <strong>API keys</strong>
    <span>Script AdventureLog or connect your own tools through the REST API.</span>
    <em>Created by each user</em>
  </a>
  <a class="al-card" href="./analytics">
    <strong>Umami analytics</strong>
    <span>Add privacy-friendly usage analytics to your instance.</span>
    <em>Environment variables</em>
  </a>
</div>
