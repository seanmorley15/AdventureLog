# Google Maps

By default AdventureLog uses OpenStreetMap to search for places and look up addresses. With a Google Maps API key, it uses Google instead for place search, place details, recommendations, and addresses.

**Who sets it up:** the server admin, once, for everyone on the server. Users see it as on or off under **Settings → Integrations**.

## Create an API key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and sign in, or create an account.
2. Open the project dropdown in the top bar, choose **New Project**, name it (for example `AdventureLog Maps`), and choose **Create**. Make sure the new project is selected.
3. Open the navigation menu and go to **Google Maps Platform**. Google may ask you to link a billing account, even if your usage stays within the free monthly usage. See [Costs](#costs).
4. Go to **APIs & Services**, filter products by **Places** and tiers by **Essentials**, and enable the **Geocoding API** and the **Places API (New)**.
5. Go to **Keys & Credentials**, choose **Create credentials → API key**, and copy the key.
6. Restrict the key to the **Geocoding API** and the **Places API (New)**. See [Securing the API key](#securing-the-api-key).

::: tip
AdventureLog versions _v0.10.0 and lower_ use the legacy **Places API** instead of **Places API (New)**.
:::

## Server setup

Add the key to your env file (`.env` for Standard Deployment, `.env.advanced` for Advanced, where it belongs to the backend `server` service), then restart:

```env
GOOGLE_MAPS_API_KEY=your_api_key
```

## What AdventureLog uses Google for

| Feature | Google API method |
| ------- | ----------------- |
| Searching for a place when adding a location | Places API (New): Text Search |
| Details of a selected place | Places API (New): Place Details |
| Recommendations near a location | Places API (New): Nearby Search |
| Turning coordinates into an address | Geocoding API, plus a Places API (New) Nearby Search for the place name |
| Photos shown with search results and recommendations | Places API (New): Place Photos |

## Securing the API key

Photos in search results and recommendations are loaded by the browser from a Google URL that contains the API key, so anyone who can use your AdventureLog server can see the key. Restrict it.

Edit the key under **Keys & Credentials** and set:

- **APIs**: restrict the key to the **Geocoding API** and the **Places API (New)**.
- **Application**: optionally, restrict the key to the public **IP address(es)** of your server.

::: info
Photos in search results and recommendations are loaded directly by the browser. With an IP address restriction, photos only load for users whose public IP address is on the list (for example, users on the same network as the server); search and recommendations still work for everyone.
:::

## Costs

Google Maps Platform bills each API method per request, with free usage each month per API method. See [Google Maps Platform pricing](https://developers.google.com/maps/billing-and-pricing/pricing#places-pricing) for current free limits and prices for the Essentials APIs.

## Capping usage

To put a hard limit on usage, lower the per-day quotas. This is only possible after the free trial has finished.

1. In the Google Cloud Console, go to **Google Maps Platform** → **Quotas**.
2. Select the API.
3. Tick the box next to a per-day quota, click **Edit**, enter a new value and submit.

To stay within the free monthly usage, divide it by 31: for example, `32` per day for `SearchTextRequest`, `GetPlaceRequest`, `SearchNearbyRequest` and `GetPhotoMediaRequest`. Do the same for the **Geocoding API** (`322` per day). When a quota is reached, Google refuses further requests until midnight Pacific Time.

## Troubleshooting

If the backend logs show `Google recommendations provider error: Google Places API error`, or search falls back to OpenStreetMap results, check that the **Places API (New)** is enabled for your project and allowed in the key's API restrictions.
