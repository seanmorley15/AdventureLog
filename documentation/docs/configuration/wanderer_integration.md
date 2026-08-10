# Wanderer Integration

[Wanderer](https://wanderer.to) is a self-hosted trail database. Integrating Wanderer with AdventureLog allows you to import trails directly into your locations, making it easier to plan and track your outdoor adventures.

## Wanderer Integration Setup

1. In your Wanderer instance, create an API key (format: `wanderer_key_...`).
2. Navigate to the AdventureLog settings page.
3. Click on the **Integrations** tab.
4. Find the **Wanderer** section and enter your Wanderer server URL and API key.
5. Click **Connect to Wanderer** to save and verify the connection.

AdventureLog stores your API key securely on the server and uses it only to call the Wanderer API on your behalf. The key is never returned to the browser after it is saved.

### Important Notes

1. The URL to the Wanderer server must be accessible from the AdventureLog server. Values like `localhost` or `127.0.0.1` often fail when AdventureLog runs in Docker or on another host.
2. If you upgrade from the older username/password integration, you must disconnect and reconnect with an API key. Existing Wanderer links on locations will not carry over automatically.
3. If your API key is revoked or invalid, update it in Settings → Integrations → Wanderer (Edit).

## Importing Wanderer Trails

1. Open the create/edit location popup in AdventureLog.
2. Navigate to the **Media** tab and scroll down to the **Trail Management** section.
3. Click the **Add Wanderer Trail** button.
4. A search input will appear. Type the name of the trail you want to import.
5. Select the desired trail from the search results and click the link icon to import it into your location.
6. The imported trail will be added to your location's trails list, and you can view its details, including distance, elevation gain, and more.

### Open in Wanderer links

Wanderer trail pages use this URL pattern:

`{your-server}/trail/view/@{author-username}@{author-domain}/{trail-id}`

Example: `https://wanderer.seanmorley.com/trail/view/@seanmorley15@wanderer.seanmorley.com/25145802f15fe7a`

AdventureLog stores `wanderer_author_username` and `wanderer_author_domain` on each linked trail (from `expand.author` on the Wanderer API). The API response includes `wanderer_link` built from those fields plus your connected server URL.

Older linked trails without author metadata are backfilled automatically the next time they are loaded (AdventureLog calls `GET /api/v1/trail/{id}?expand=author`).

Enjoy exploring new trails with Wanderer and AdventureLog! If you encounter any issues or have questions about the integration, feel free to reach out to the AdventureLog community!
