# Easypanel

[Easypanel](https://easypanel.io/) is a server control panel. Its official AdventureLog template deploys the app without any Docker commands.

## Install

1. Open your Easypanel dashboard and create or open a project.
2. Choose **+ Add Service**, then **Templates**.
3. Search for **AdventureLog**, select it, and choose **Create**.

Easypanel creates the PostGIS database, runs the frontend and backend containers, and exposes them on a domain.

![AdventureLog deployed on Easypanel](/easypanel_deployed.png)

Set `SITE_URL` to your public HTTPS address, so sign-in and photo URLs match. See [URL and networking](../configuration/environment_variables.md#url-and-networking). The [template page](https://easypanel.io/templates/adventurelog) has more details.

## Next steps

- [First Steps](first_steps.md): sign in, secure the admin account, and decide who can join.
