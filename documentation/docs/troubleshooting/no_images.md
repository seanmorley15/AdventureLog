# Images Not Displaying

**Symptom:** locations and collections load, but their photos show as broken images.

**Cause:** the browser loads each photo from a URL that AdventureLog builds from its public address. If that address is wrong, or your browser can't reach it, the photos fail.

## Fix on Standard Deployment

1. Set `SITE_URL` in `.env` to the address you open in the browser, including `http://` or `https://` and any port.
2. Restart: `docker compose --env-file .env up -d`.

Photo URLs are built from `SITE_URL`, so photos break when you open the app at a different address, such as a LAN IP while `SITE_URL` is your domain.

## Fix on Advanced Deployment

1. Right-click a broken image and open it in a new tab. Note the address it tries to load.
2. Set `PUBLIC_URL` in `.env.advanced` to the backend's public address, the one your browser can reach. For example `https://adventurelog.example.com` behind a reverse proxy, or `http://192.168.1.20:8016` without one.
3. Make sure `CSRF_TRUSTED_ORIGINS` lists both the frontend and backend addresses.
4. Behind a reverse proxy, check that `/media` is sent to the backend.
5. Restart the containers.

## Using S3 storage

Photos load from your bucket or `AWS_S3_CUSTOM_DOMAIN`. Open a broken image in a new tab to see the error from the storage provider. See [S3 Media Storage](../configuration/s3_storage.md#troubleshooting).
