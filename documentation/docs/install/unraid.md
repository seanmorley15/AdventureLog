# Installation with Unraid

AdventureLog is available in the Unraid Community Applications store. You can install it by searching for "AdventureLog" in the Community Applications store.

Community Applications Page: [AdventureLog on CA Store](https://unraid.net/community/apps?q=Adventurelog)

## Installation Configuration

It is recommended to install applications in this order.

## Database

- To find the Database Application, search for `PostGIS` on the Unraid App Store and fill out the fields as follows:
- Ensure that the POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB are set in the PostGIS container if not add them custom variables

![/static/img/unraid-config-2.png](/static/img/unraid-config-2.png)

## Backend

- Cache Configuration: This option is useful only if your appdata share is stored on a cache drive, which is used to speed up read/write operations for your containerized applications.
- Note: if your running the server in a docker network that is other than "host" (for example "bridge") than you need to add the IP of the host machine in the CSRF Trusted Origins variable.

![/static/img/unraid-config-1.png](/static/img/unraid-config-1.png)

## Frontend

- By default, the frontend connects to the backend using `http://server:8000`. This will work if both the frontend and backend are on the same network. Otherwise, you’ll need to configure it to use the exposed port (default: 8016).

![/static/img/unraid-config-3.png](/static/img/unraid-config-3.png)


