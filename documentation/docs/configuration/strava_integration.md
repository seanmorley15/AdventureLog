# Strava

[Strava](https://www.strava.com/) tracks runs, rides, hikes, and other workouts. Connect it to import your Strava activities into the visits of your locations, with distance, duration, elevation gain, and more.

**Who sets it up:** the server admin creates a Strava API application once. Then each user connects their own Strava account.

## Server setup

1. Sign in to Strava and open the [API applications page](https://www.strava.com/settings/api). Choose **Create a New Application**.
2. Fill in:
   - **Application Name**: `AdventureLog`, or any name.
   - **Website**: your AdventureLog address, for example `https://adventurelog.example.com`.
   - **Authorization Callback Domain**: the domain only, for example `adventurelog.example.com`.
3. Accept the API terms and choose **Create**. Copy the **Client ID** and **Client Secret**.
4. Add them to your env file (`.env` for Standard Deployment, `.env.advanced` for Advanced) and restart:

   ```env
   STRAVA_CLIENT_ID=your_client_id
   STRAVA_CLIENT_SECRET=your_client_secret
   ```

## Connect your account

1. Go to **Settings → Integrations → Strava** and choose **Connect Account**.
2. Sign in to Strava and allow AdventureLog to read your activities.
3. Strava sends you back to AdventureLog, now connected.

If the Strava section says it isn't enabled on this instance, the server setup above hasn't been done.

## Use it

1. Open a location and add or edit a visit.
2. On the visit, choose the Strava button to search your activities from that time.
3. Import an activity. It brings in the distance, duration, elevation gain, and other details.
4. To add the route, choose **Download GPX**, then drop the downloaded file into the visit's GPX field. Strava's API doesn't let AdventureLog fetch the track itself.

[Endurain](endurain_integration.md) imports tracks without the manual download, if you use it.
