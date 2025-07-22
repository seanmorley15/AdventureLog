# Installation with Truenas Scale

TrueNAS Scale is an open-source, Linux-based operating system designed for managing storage servers. It supports advanced features like ZFS file system, virtualization, containers (including Docker), and clustering.

It is fairly simple to set up Truenas with AdventureLog.

## Deploy AdventureLog as a Custom App

Navigate to Apps first. Under Discover you will see the 3 dots menu. Click on 'Install via YAML'.

Add the following to the popup and click save.

The following values needs to be changed to achieve a working solution.
- `Truenas_Server_IP` - The local IP address of your truenas server (eg. 192.168.1.10).

```yaml
services:
  db:
    environment:
      POSTGRES_DB: database
      POSTGRES_PASSWORD: your_postgres_password
      POSTGRES_USER: adventure
    image: postgis/postgis:15-3.3
    restart: unless-stopped
    volumes:
      - postgres-data:/var/lib/postgresql/data/
  server:
    depends_on:
      - db
    environment:
      CSRF_TRUSTED_ORIGINS: http://[Truenas_Server_IP]:8016,http://[Truenas_Server_IP]:8015
      DEBUG: 'false'
      DJANGO_ADMIN_EMAIL: adventurelog-admin@yourdomain.com
      DJANGO_ADMIN_PASSWORD: your_admin_password
      DJANGO_ADMIN_USERNAME: admin
      FRONTEND_URL: http://[Truenas_Server_IP]:8015
      PGDATABASE: database
      PGHOST: db
      PGPASSWORD: your_postgres_password
      PGUSER: adventure
      PUBLIC_URL: http://[Truenas_Server_IP]:8016
      SECRET_KEY: your_secret_key
      BACKEND_PORT: 8016
    image: ghcr.io/seanmorley15/adventurelog-backend:latest
    restart: unless-stopped
    ports:
      - "${BACKEND_PORT:-8016}:80"
    volumes:
      - adventurelog-media:/code/media
  web:
    depends_on:
      - server
    environment:
      BODY_SIZE_LIMIT: '100000'
      PUBLIC_SERVER_URL: http://server:8000
    image: ghcr.io/seanmorley15/adventurelog-frontend:latest
    ports:
      - ${FRONTEND_PORT:-8015}:3000
    restart: unless-stopped
version: '3.9'
volumes:
  adventurelog-media: Null
  postgres-data: Null

```

## Login to AdventureLog

You should be able to log in with the defined user credentials at http://[Truenas_Server_IP]:8015 
For more details.

## How to expose behind a proxy (extra step)

In case you use want to host your service behind a proxy like nginx, modify the following variables.
- `CSRF_TRUSTED_ORIGINS` - should point to your domain that is proxied to port 8015
- `FRONTEND_URL` - should point to your domain that is proxied to port 8015
- `PUBLIC_URL` - should point to your domain that is proxied to port 8016