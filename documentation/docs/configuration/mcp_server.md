# MCP Server (AI Assistants)

The AdventureLog MCP server lets AI assistants that support the [Model Context Protocol](https://modelcontextprotocol.io) work with your data: find and create **locations**, build **collections** with lodging, transportation, notes and checklists, plan a collection day by day, and keep track of the countries, regions and cities you have visited. For example: _"Make a collection for Acadia National Park, June 3 to 6. Add the top food spots near Bar Harbor, a hotel, and fill a day-by-day plan."_

It is a separate, optional container. It talks to your AdventureLog through the normal [REST API](api_keys.md) as you, so it sees and changes only what your API key could.

::: warning Your data goes to the AI
Whatever the assistant reads through the tools is sent to the AI provider you use. API keys have full access to your account (there are no read-only keys yet), so only connect assistants you trust, and revoke the key under **Settings → Security** when you stop using it.
:::

## Set it up

1. **Create an API key** in **Settings → Security**. See [API Keys](api_keys.md).

2. **Add the service** to your `docker-compose.yml`, under `services:` next to `app`:

   ```yaml
   mcp:
     image: ghcr.io/seanmorley15/adventurelog-mcp:latest
     container_name: adventurelog-mcp
     restart: unless-stopped
     environment:
       ADVENTURELOG_URL: http://app:80
       ADVENTURELOG_PUBLIC_URL: ${SITE_URL:-http://localhost:8015}
     ports:
       - "8017:8017"
     depends_on:
       app:
         condition: service_healthy
   ```

   Then run `docker compose up -d`.

   On [Advanced Deployment](../install/docker.md) set `ADVENTURELOG_URL` to the backend container, `http://server:80`. A ready-made file with the MCP service already added is in the repository: [`docker/docker-compose.advanced-mcp.yml`](https://github.com/seanmorley15/AdventureLog/blob/main/docker/docker-compose.advanced-mcp.yml). Start it with `docker compose --env-file .env.advanced -f docker/docker-compose.advanced-mcp.yml up -d --wait`.

3. **Connect your assistant** to `http://localhost:8017/mcp`, sending your key as `Authorization: Bearer al_your_key` (or `X-API-Key: al_your_key`). The key lives in the assistant's settings, never in the compose file, so each person who connects uses their own account. With Claude Code:

   ```bash
   claude mcp add --transport http adventurelog http://localhost:8017/mcp \
     --header "Authorization: Bearer al_your_key"
   ```

   Other assistants need a client that supports MCP servers over HTTP (Streamable HTTP) with custom headers.

4. **Check it** by asking the assistant to run `whoami`. It should answer with your username and AdventureLog version.

::: warning Use HTTPS if it is reachable from the internet
The API key travels in a header. Keep port 8017 on your own network, or put the MCP server behind a reverse proxy with HTTPS, the same way as AdventureLog itself.
:::

## Settings

| Variable                  | Default                    | What it does                                                                                               |
| ------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `ADVENTURELOG_URL`        | `http://app:80`            | Where the MCP server reaches AdventureLog.                                                                 |
| `ADVENTURELOG_PUBLIC_URL` | same as `ADVENTURELOG_URL` | Sent as the `Origin` header. Set it to your `SITE_URL`.                                                    |
| `ADVENTURELOG_API_KEY`    |                            | For running the server over stdio only. Over HTTP it is ignored: each client sends its own key.            |
| `MCP_PORT`                | `8017`                     | Port inside the container.                                                                                 |
| `MCP_ALLOWED_HOSTS`       |                            | Comma-separated `Host` values to accept. Set it when you expose the server on a domain.                    |
| `MCP_ALLOW_DESTRUCTIVE`   | `false`                    | Turns on the delete tools. Off by default: the assistant can create and change things but not delete them. |

## What the assistant can do

| Area              | Examples                                                                                                    |
| ----------------- | ----------------------------------------------------------------------------------------------------------- |
| Find              | Search everything, list and read locations and collections, list categories and tags                        |
| Look up places    | Search the map, get a place's details, check for duplicates before saving, find things to see or eat nearby |
| Create and change | Locations, visits, collections, lodgings, transportation, notes and checklists                              |
| Plan              | Read a collection's day-by-day plan, put items on days, reorder, set times, name days, change its length    |
| World travel      | Countries, regions and cities with what you have visited, mark or unmark them, totals                       |
| Delete (opt-in)   | Locations, collections and their contents, with `MCP_ALLOW_DESTRUCTIVE=true`                                |

Repeating a create does not duplicate it, and an assistant can pass a record's `version` when editing so a change you made in the meantime is not overwritten.

## Troubleshooting

- **"No AdventureLog API key was sent"**: the client did not send the header. Check the `Authorization: Bearer al_…` header in its MCP settings.
- **"Could not reach AdventureLog"**: `ADVENTURELOG_URL` is wrong from inside the container, where `localhost` is the container itself. Use the compose service name (`http://app:80`). If AdventureLog runs outside Docker (for example a development setup), use `http://host.docker.internal:8000`, the backend, which the container can reach on Docker Desktop. Docker on plain Linux needs `extra_hosts: ["host.docker.internal:host-gateway"]` on the service, and a server that listens on all interfaces rather than only `127.0.0.1`.
- **"Invalid or expired API key"**: the key was deleted or mistyped. Create a new one.
- **Nothing happens when deleting**: delete tools are off unless you set `MCP_ALLOW_DESTRUCTIVE=true`.
