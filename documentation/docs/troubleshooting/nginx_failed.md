# Nginx Failed to Start

**Symptom:** the backend container keeps restarting, and its log shows `Starting nginx: nginx failed!`.

**Cause:** backend images from before January 2024 had an nginx configuration that only worked when the backend service in the compose file was named `server`. Renaming the service broke it.

## Fix

Update to the current images. See [Updating](../configuration/updating.md). The nginx inside today's images talks to Django on `127.0.0.1` and doesn't depend on the service name, so you can name the service anything.

If you can't update yet, rename the backend service back to `server` in your compose file.

If current images still show this error, ask in the [Discord server](https://discord.gg/wRbQ9Egr8C) or open a [GitHub issue](https://github.com/seanmorley15/AdventureLog/issues) with the container log.
