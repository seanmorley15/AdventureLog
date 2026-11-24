# Immich

[Immich](https://immich.app/) is a self-hosted photo and video library. Connect it to pick photos from your Immich library for any location, instead of uploading them again.

**Who sets it up:** each user connects their own Immich account. The server admin doesn't need to do anything.

## Connect your account

1. **Create an API key in Immich.** Open your avatar menu, go to **Account Settings → API Keys**, and choose **New API Key**. Name it `AdventureLog` and give it these permissions: `asset.read`, `asset.view`, `album.read`, `library.read`, `user.read`. Copy the key.
2. **Add it to AdventureLog.** Go to **Settings → Integrations → Immich** and enter:
   - **Immich Server URL**: the address of the Immich API, which usually ends in `/api`, for example `https://immich.example.com/api`. AdventureLog's server connects to it, so use an address that server can reach. `localhost` usually doesn't work in Docker; use your server's IP address or domain.
   - **Immich API Key**: the key from step 1.
   - **Copy Images Locally** (optional): stores a copy of each photo you pick on the AdventureLog server, so it still shows when Immich is offline. Uses more disk space.
3. Choose **Enable Integration**.

## Use it

When you add photos to a location, choose Immich and find photos in one of three ways:

- **By Date**: photos from one day. If the location has a visit, it opens on the latest visit date.
- **By Album**: photos from an Immich album.
- **Search using Immich**: Immich's own search.

A location with Immich photos can also open its spot on your Immich map.

## Troubleshooting

| Problem | Fix |
| ------- | --- |
| "Error connecting to Immich server" | Check that the URL ends in `/api` and that the AdventureLog server can reach it. See [An integration can't connect](../troubleshooting/common_issues.md#an-integration-can-t-connect). |
| Validation fails | Check the API key and its permissions. |
| Immich photos don't appear on maps | Run `backfill_image_coordinates` for photos added before their location was stored. See [Management Commands](management_commands.md#photos-and-files). |
