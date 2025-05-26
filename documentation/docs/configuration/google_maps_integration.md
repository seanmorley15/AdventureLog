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
8. Navigate to **Google Maps Platform**.
9. Once in the Maps Platform, click on **Keys & Credentials** in the left sidebar.
10. Click on **Create credentials** and select **API key**.
11. A dialog will appear with your new API key. Copy this key for later use.

<!-- To prevent misuse:

1. Click the **Edit icon** next to your new API key.
2. Under **Application restrictions**, choose one:
   - Choose **Websites** as the restriction type.
   - Add the domain of the AdventureLog **backend** (e.g., `https://your-adventurelog-backend.com`). -->

## Configuration in AdventureLog

Set the API key in your environment file or configuration under the backend service of AdventureLog. This is typically done in the `docker-compose.yml` file or directly in your environment variables `.env` file.

```env
GOOGLE_MAPS_API_KEY=your_api_key_here
```

Once this is set, AdventureLog will be able to utilize Google Maps services for geocoding and location searches instead of relying on the default OpenStreetMap services.
