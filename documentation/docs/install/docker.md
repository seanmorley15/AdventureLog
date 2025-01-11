# Docker 🐋

Docker is the preferred way to run AdventureLog on your local machine. It is a lightweight containerization technology that allows you to run applications in isolated environments called containers.
**Note**: This guide mainly focuses on installation with a linux based host machine, but the steps are similar for other operating systems.

## Prerequisites

- Docker installed on your machine/server. You can learn how to download it [here](https://docs.docker.com/engine/install/).

## Getting Started

Get the `docker-compose.yml` file from the AdventureLog repository. You can download it from [here](https://github.com/seanmorley15/AdventureLog/blob/main/docker-compose.yml) or run this command to download it directly to your machine:

::: tip

If running on an ARM based machine, you will need to use a different PostGIS Image. It is recommended to use the `tobi312/rpi-postgresql-postgis:15-3.3-alpine-arm` image or a custom version found [here](https://hub.docker.com/r/tobi312/rpi-postgresql-postgis/tags). The AdventureLog containers are ARM compatible.

:::

```bash
wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/main/docker-compose.yml
```

## Configuration

Here is a summary of the configuration options available in the `docker-compose.yml` file:

<!-- make a table with colum name, is required, other -->

### Frontend Container (web)

| Name                | Required  | Description                                                                                                                                                   | Default Value         |
| ------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `PUBLIC_SERVER_URL` | Yes       | What the frontend SSR server uses to connect to the backend.                                                                                                  | http://server:8000    |
| `ORIGIN`            | Sometimes | Not needed if using HTTPS. If not, set it to the domain of what you will acess the app from.                                                                  | http://localhost:8015 |
| `BODY_SIZE_LIMIT`   | Yes       | Used to set the maximum upload size to the server. Should be changed to prevent someone from uploading too much! Custom values must be set in **kiliobytes**. | Infinity              |

### Backend Container (server)

| Name                    | Required | Description                                                                                                                                   | Default Value         |
| ----------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `PGHOST`                | Yes      | Databse host.                                                                                                                                 | db                    |
| `PGDATABASE`            | Yes      | Database.                                                                                                                                     | database              |
| `PGUSER`                | Yes      | Database user.                                                                                                                                | adventure             |
| `PGPASSWORD`            | Yes      | Database password.                                                                                                                            | changeme123           |
| `DJANGO_ADMIN_USERNAME` | Yes      | Default username.                                                                                                                             | admin                 |
| `DJANGO_ADMIN_PASSWORD` | Yes      | Default password, change after inital login.                                                                                                  | admin                 |
| `DJANGO_ADMIN_EMAIL`    | Yes      | Default user's email.                                                                                                                         | admin@example.com     |
| `PUBLIC_URL`            | Yes      | This needs to match the outward port of the server and be accessible from where the app is used. It is used for the creation of image urls.   | http://localhost:8016 |
| `CSRF_TRUSTED_ORIGINS`  | Yes      | Need to be changed to the orgins where you use your backend server and frontend. These values are comma seperated.                            | http://localhost:8016 |
| `FRONTEND_URL`          | Yes      | This is the publically accessible url to the **frontend** container. This link should be accessable for all users. Used for email generation. | http://localhost:8015 |

## Running the Containers

To start the containers, run the following command:

```bash
docker compose up -d
```

Enjoy AdventureLog! 🎉
