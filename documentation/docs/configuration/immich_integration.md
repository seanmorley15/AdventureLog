# Immich Integration

### What is Immich?

<!-- immich banner -->

![Immich Banner](https://repository-images.githubusercontent.com/455229168/ebba3238-9ef5-4891-ad58-a3b0223b12bd)

Immich is a self-hosted, open-source platform that allows users to backup and manage their photos and videos similar to Google Photos, but with the advantage of storing data on their own private server, ensuring greater privacy and control over their media.

- [Immich Website and Documentation](https://immich.app/)
- [GitHub Repository](https://github.com/immich-app/immich)

### How to integrate Immich with AdventureLog?

To integrate Immich with AdventureLog, you need to have an Immich server running and accessible from where AdventureLog is running.

1. Obtain the Immich API Key from the Immich server.
   - In the Immich web interface, click on your user profile picture, go to `Account Settings` > `API Keys`.
   - Click `New API Key` and name it something like `AdventureLog`.
   - Copy the generated API Key, you will need it in the next step.
2. Go to the AdventureLog web interface, click on your user profile picture, go to `Settings` and scroll down to the `Immich Integration` section.
   - Enter the URL of your Immich server, e.g. `https://immich.example.com`. Note that `localhost` or `127.0.0.1` will probably not work because Immich and AdventureLog are running on different docker networks. It is recommended to use the IP address of the server where Immich is running ex `http://my-server-ip:port` or a domain name.
   - Paste the API Key you obtained in the previous step.
   - Click `Enable Immich` to save the settings.
3. Now, when you are adding images to an adventure, you will see an option to search for images in Immich or upload from an album.

Enjoy the privacy and control of managing your travel media with Immich and AdventureLog! 🎉


### How to use the pictures from Immich, but not save them in AdventureLog?

This is possible with the environment variable `VITE_IMMICH_UPLOAD_URLS_ONLY` on the frontend/web container. When set to `true`, AdventureLog will only use the pictures from Immich and not save them in AdventureLog. This can be useful if you want to save storage space on your AdventureLog server but still want to use the pictures from Immich in your adventures.

1. Go to the AdventureLog server and open the `docker-compose` file.
2. Add the following environment variable to the `web` service:
   ```yaml
   environment:
     - VITE_IMMICH_UPLOAD_URLS_ONLY=true
   ```

3. Save the file and restart the AdventureLog server with `docker-compose up -d`.

This saves the URL's in the format of: `https://<frontend-url>/immich/b8a8b977-37b6-48fe-b4a0-1739ed7997dc`. Changing the URL where immich is hosted will not break this, but changing the frontend URL will break the links. To fix this, run the following migration inside your postgres database:

```sql
UPDATE adventures_adventureimage SET external_url = REPLACE(external_url, 'http://127.0.0.1:5173/', 'https://https://adventurelog.app/');
```