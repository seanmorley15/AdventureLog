# Easypanel

[Easypanel](https://easypanel.io/) is a server control panel that can deploy AdventureLog with one click using its official template, without needing to manually run Docker commands.

1. Open your Easypanel dashboard and create (or open) a project
2. Click **+ Add Service** and choose **Templates**
3. Search for **AdventureLog** and select it
4. Click **Create** to deploy the service

Easypanel provisions the required PostGIS database automatically and runs the frontend and backend containers for you, exposing them through a domain.

![AdventureLog deployed on Easypanel](/easypanel_deployed.png)

Set `SITE_URL` to your public HTTPS URL so Django CSRF and SvelteKit origins stay correct. See [Environment Variables](../configuration/environment_variables.md#url-and-networking).

See the [official AdventureLog template on Easypanel](https://easypanel.io/templates/adventurelog) for more details.
