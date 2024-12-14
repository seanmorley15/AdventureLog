# AdventureLog: Embark, Explore, Remember. 🌍

### _"Never forget an adventure with AdventureLog - Your ultimate travel companion!"_

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/seanmorley15)

- **[Documentation](https://adventurelog.app)**
- **[Demo](https://demo.adventurelog.app)**
- **[Join the AdventureLog Community Discord Server](https://discord.gg/wRbQ9Egr8C)**

# Table of Contents

- [Installation](#installation)
  - [Docker 🐋](#docker-)
    - [Prerequisites](#prerequisites)
    - [Getting Started](#getting-started)
    - [Configuration](#configuration)
      - [Frontend Container (web)](#frontend-container-web)
      - [Backend Container (server)](#backend-container-server)
      - [Proxy Container (nginx) Configuration](#proxy-container-nginx-configuration)
    - [Running the Containers](#running-the-containers)
- [Screenshots 🖼️](#screenshots)
- [About AdventureLog](#about-adventurelog)
- [Attribution](#attribution)

# Installation

# Docker 🐋

Docker is the preferred way to run AdventureLog on your local machine. It is a lightweight containerization technology that allows you to run applications in isolated environments called containers.
**Note**: This guide mainly focuses on installation with a linux based host machine, but the steps are similar for other operating systems.

## Prerequisites

- Docker installed on your machine/server. You can learn how to download it [here](https://docs.docker.com/engine/install/).

## Getting Started

Get the `docker-compose.yml` file from the AdventureLog repository. You can download it from [here](https://github.com/seanmorley15/AdventureLog/blob/main/docker-compose.yml) or run this command to download it directly to your machine:

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

| Name                    | Required | Description                                                                                                                                 | Default Value         |
| ----------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `PGHOST`                | Yes      | Databse host.                                                                                                                               | db                    |
| `PGDATABASE`            | Yes      | Database.                                                                                                                                   | database              |
| `PGUSER`                | Yes      | Database user.                                                                                                                              | adventure             |
| `PGPASSWORD`            | Yes      | Database password.                                                                                                                          | changeme123           |
| `DJANGO_ADMIN_USERNAME` | Yes      | Default username.                                                                                                                           | admin                 |
| `DJANGO_ADMIN_PASSWORD` | Yes      | Default password, change after inital login.                                                                                                | admin                 |
| `DJANGO_ADMIN_EMAIL`    | Yes      | Default user's email.                                                                                                                       | admin@example.com     |
| `PUBLIC_URL`            | Yes      | This needs to match the outward port of the server and be accessible from where the app is used. It is used for the creation of image urls. | http://localhost:8016 |
| `CSRF_TRUSTED_ORIGINS`  | Yes      | Need to be changed to the orgins where you use your backend server and frontend. These values are comma seperated.                          | http://localhost:8016 |
| `FRONTEND_URL`          | Yes      | This is the publicly accessible url to the **frontend** container. This link should be accessible for all users. Used for email generation. | http://localhost:8015 |

## Running the Containers

To start the containers, run the following command:

```bash
docker compose up -d
```

Enjoy AdventureLog! 🎉

# Screenshots

![Adventure Page](screenshots/adventures.png)
Displaying the adventures you have visited and the ones you plan to embark on. You can also filter and sort the adventures.

![Detail Page](screenshots/details.png)
Shows specific details about an adventure, including the name, date, location, description, and rating.

![Edit](screenshots/edit.png)

![Map Page](screenshots/map.png)
View all of your adventures on a map, with the ability to filter by visit status and add new ones by click on the map.

![Itinerary Page](screenshots/itinerary.png)

![Country Page](screenshots/countries.png)

![Region Page](screenshots/regions.png)

# About AdventureLog

AdventureLog is a Svelte Kit and Django application that utilizes a PostgreSQL database. Users can log the adventures they have experienced, as well as plan future ones. Key features include:

- Logging past adventures with fields like name, date, location, description, and rating.
- Planning future adventures with similar fields.
- Tagging different activity types for better organization.
- Viewing countries, regions, and marking visited regions.

AdventureLog aims to be your ultimate travel companion, helping you document your adventures and plan new ones effortlessly.

AdventureLog is licensed under the GNU General Public License v3.0.

<!-- ## Screenshots 🖼️

![Visited Log](https://github.com/seanmorley15/AdventureLog/blob/main/brand/screenshots/visited.png?raw=true)
![Planner Log](https://github.com/seanmorley15/AdventureLog/blob/main/brand/screenshots/ideas.png?raw=true)
![Country List](https://github.com/seanmorley15/AdventureLog/blob/main/brand/screenshots/countrylist.png?raw=true)
![Region List for the United States](https://github.com/seanmorley15/AdventureLog/blob/main/brand/screenshots/regions.png?raw=true)

## Roadmap 🛣️

- Improved mobile device support
- Password reset functionality
- Improved error handling
- Handling of adventure cards with variable width -->

# Attribution

- Logo Design by [nordtechtiger](https://github.com/nordtechtiger)
- WorldTravel Dataset [dr5hn/countries-states-cities-database](https://github.com/dr5hn/countries-states-cities-database)
