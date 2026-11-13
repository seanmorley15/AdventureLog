# Wanderer

[Wanderer](https://wanderer.to) is a self-hosted trail database. Connect it to link Wanderer trails to your locations, with their distance, elevation gain, and a link back to the trail.

**Who sets it up:** each user connects their own Wanderer account. The server admin doesn't need to do anything.

## Connect your account

1. In Wanderer, create an API key. It starts with `wanderer_key_`.
2. In AdventureLog, go to **Settings → Integrations → Wanderer**.
3. Enter your Wanderer **Server URL** and **API Key**, then connect.

AdventureLog's server connects to Wanderer, so use an address that server can reach. `localhost` and `127.0.0.1` usually don't work in Docker. The key stays on the server and is never sent back to your browser.

## Use it

1. Open a location to edit it, and go to the **Media** tab.
2. Under **Trail Management**, choose **Add Wanderer Trail**.
3. Search for the trail by name, and choose the link icon on the result.

The trail joins the location's trails, with its distance and elevation gain, and an **Open in Wanderer** link.

## Troubleshooting

| Problem | Fix |
| ------- | --- |
| Can't connect | Check the URL and that the AdventureLog server can reach it. See [An integration can't connect](../troubleshooting/common_issues.md#an-integration-can-t-connect). |
| Trails stopped loading | The API key was revoked or expired. Edit the integration under **Settings → Integrations → Wanderer** and enter a new key. |
| Upgraded from the old username and password connection | Disconnect and connect again with an API key. Trails linked the old way aren't carried over. |

## For developers

Wanderer trail pages use the address `{server}/trail/view/@{author-username}@{author-domain}/{trail-id}`. AdventureLog stores the author's username and domain on each linked trail, and returns the full address as `wanderer_link` in the API. Trails linked before this was stored are filled in the next time they load.
