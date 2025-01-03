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
   - Enter the URL of your Immich server, e.g. `https://immich.example.com`.
   - Paste the API Key you obtained in the previous step.
   - Click `Enable Immich` to save the settings.
3. Now, when you are adding images to an adventure, you will see an option to search for images in Immich or upload from an album.

Enjoy the privacy and control of managing your travel media with Immich and AdventureLog! 🎉
