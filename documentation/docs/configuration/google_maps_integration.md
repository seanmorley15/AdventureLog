# Google Maps Integration

To enable Google Maps integration in AdventureLog, you'll need to create a Google Maps API key. This key allows AdventureLog to use Google Maps services such as geocoding and location search throughout the application.

Follow the steps below to generate your own API key:

## Google Cloud Console Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create an account if you don't have one in order to access the console.
3. Click on the project dropdown in the top bar.
4. Click **New Project**.
5. Name your project (e.g., `AdventureLog Maps`) and click **Create**.
6. Once the project is created, ensure it is selected in the project dropdown.
7. Click on the **Navigation menu** (three horizontal lines in the top left corner).
8. Navigate to **Google Maps Platform**. Google may ask you to link a billing account (payment details) to the project, even if your usage stays within the free monthly usage. See [Costs](#costs).
9. Click on **Keys & Credentials** in the left sidebar.
10. Click on **Create credentials** and select **API key**.
11. A dialog will appear with your new API key. Copy this key for later use.
12. Restrict the key to the **Geocoding API** and the **Places API (New)**.
13. Click on **APIs & Services** in the left sidebar.
14. Filter product by Places and tiers by Essentials and enable both the Geocoding API and the Places API (New).

::: tip
AdventureLog versions _v0.10.0 and lower_ use the legacy **Places API** instead of **Places API (New)**.
:::

## Configuration in AdventureLog

Set the API key in your environment file or configuration under the backend service of AdventureLog. This is typically done in the `docker-compose.advanced.yml` file or directly in your environment variables `.env.advanced` file.

```env
GOOGLE_MAPS_API_KEY=your_api_key_here
```

## What AdventureLog uses Google for

Once this is set, AdventureLog will be able to utilize Google Maps services for geocoding and location searches instead of relying on the default OpenStreetMap services.

| Feature | Google API method |
| ------- | ----------------- |
| Searching for a place when adding a location | Places API (New): Text Search |
| Details of a selected place | Places API (New): Place Details |
| Recommendations near a location | Places API (New): Nearby Search |
| Turning coordinates into an address | Geocoding API, plus a Places API (New) Nearby Search for the place name |
| Photos shown with search results and recommendations | Places API (New): Place Photos |

## Securing the API key

Photos in search results and recommendations are loaded directly by the browser from a Google URL that contains the API key. Anyone who can use your AdventureLog instance can therefore see the key. It's therefore a good idea to set some restrictions.

Edit the key under **Keys & Credentials** and set:

- **APIs**: restrict the key to the **Geocoding API** and the **Places API (New)**.
- **Application**: optionally, restrict the key to the public **IP address(es)** of your server.

::: info
Photos in search results and recommendations are loaded directly by the browser. With an IP address restriction, therefore, photos only load for users whose public IP address is on the list (for example, users on the same network as the server); search and recommendations still work for everyone.
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
