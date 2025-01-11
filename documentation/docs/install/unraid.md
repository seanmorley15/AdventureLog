# Installation with Unraid

AdventureLog is available in the Unraid Community Applications store. You can install it by searching for "AdventureLog" in the Community Applications store.

Community Applications Page: [AdventureLog on CA Store](https://unraid.net/community/apps?q=Adventurelog)

## Installation Configuration

It is recommeneded to install applications in this order.

## Database

- To find the Database Application, search for `PostGIS` on the Unraid App Store and fill out the fields as follows:

![/static/img/unraid-config-2.png](/static/img/unraid-config-2.png)

## Backend

- Cache is only for when you have your appdata share on a cache drive

![/static/img/unraid-config-1.png](/static/img/unraid-config-1.png)

## Frontend

- By default, the frontend connects to the backend using `http://server:8000`. This will work if both the frontend and backend are on the same network. Otherwise, you’ll need to configure it to use the exposed port (default: 8016).

![/static/img/unraid-config-3.png](/static/img/unraid-config-3.png)


