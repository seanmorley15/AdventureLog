# Strava Integration

Strava is a popular platform for athletes to track their activities, share their workouts, and connect with other fitness enthusiasts. Integrating Strava with AdventureLog allows you to import your Strava activities directly into your vists, making it easier to keep track of your outdoor experiences.

To enable Strava integration in AdventureLog, you'll need to create a Strava API application. This application will provide you with the necessary client ID and client secret to authenticate with the Strava API.

Follow the steps below to generate your own Strava API credentials:

## Strava API Application Setup

1. Login to your Strava account at [Strava](https://www.strava.com/).
2. Go to the [Strava API Applications page](https://www.strava.com/settings/api).
3. Click on **Create a New Application**.
4. Fill in the application details:
   - **Application Name**: AdventureLog Strava Integration
   - **Website**: Your AdventureLog instance URL (e.g., `https://your-adventurelog-instance.com`)
   - **Authorization Callback Domain**: Your AdventureLog instance domain (e.g., `your-adventurelog-instance.com`)
5. Agree to the Strava API Terms
6. Click **Create** to generate your application.
7. After creation, you will see your **Client ID** and **Client Secret**. Keep these credentials safe as you will need them to configure AdventureLog.

## Configuration in AdventureLog

8. Once you have your Strava API credentials, you can configure AdventureLog to use them. Open your `.env` file in the root of your AdventureLog project and add the following lines:

```env
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
```

9. After adding these lines, save the file and restart your AdventureLog server to apply the changes.
10. Navigate to AdventureLog's settings page, click the integration tab, and find the Strava section.
11. Click the **Connect Account** button. This will redirect you to Strava's authorization page.
12. Log in to your Strava account and authorize AdventureLog to access your Strava data.
13. After authorization, you will be redirected back to AdventureLog, and your Strava account will be linked.

## Importing Strava Activities

The Strava integration appears on the visit create/edit part of the location edit popup. Once a visit is added, there will be a button on it to search for Strava activities. Clicking this button will search then you can import the activity into the visit. The imported activity will include details such as distance, duration, elevation gain, and more.

**Note**: Due to API limitations on Strava's side, when you import an activity, there will be a button that says **Download GPX** then you can download the GPX file of the activity and drop it into the input field of the visit. This manual action is necessary because Strava does not provide a direct way to import GPX files into AdventureLog.

Enjoy tracking your adventures with Strava and AdventureLog! If you encounter any issues or have questions about the integration, feel free to reach out to the AdventureLog community!
