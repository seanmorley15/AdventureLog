# Installation with Unraid

AdventureLog is available in the Unraid Community Applications store. You can install it by searching for `AdventureLog` in the Community Applications store, where you will find the frontend and the backend, the database can be found by searching `PostGIS`.

Community Applications Page for AdventureLog: [AdventureLog on CA Store](https://unraid.net/community/apps?q=AdventureLog)
Community Applications Page for PostGIS: [PostGIS on CA Store](https://unraid.net/community/apps?q=PostGIS)

## Installation Configuration

It is recommended to install the applications in the order of these instructions.

Also insure they are all on the same custom network so they can communicate to one another, you can create one by running the following command in your command line with example being set to your wanted name. This network will then showup for selection when making the apps/containers.
```bash
docker network create example
```

## Database

- To find the Database Application, search for `PostGIS` on the Unraid App Store and fill out the fields as shown below
- Network type should be set to your custom network
- Change the repository version to `postgis/postgis:15-3.3`
- Ensure that the POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD are set in the PostGIS container, if not then add them as custom variables, the other variables are irrelevant for this setup and should be removed.

| Name                | Required  | Description                                                                                                                                                   | Default Value         |
| ------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `POSTGRES_DB`       | Yes       | What the name of the database in PostGIS will be.                                                                                                             | N/A                   |
| `POSTGRES_USER`     | Yes       | Name of the user generated on first start that will have access to the database                                                                               | N/A                   |
| `POSTGRES_PASSWORD` | Yes       | Password of the user that will be generated on first start                                                                                                    | N/A                   |

![/static/img/unraid-config-2.png](/unraid-config-2.png)

## Backend

- Network type should be set to your custom network
- **Note:** If you're running the server in a docker network that is other than "host" (for example "bridge") than you need to add the IP of the host machine in the CSRF Trusted Origins variable instead of using localhost, this is only necessary when accessing locally, otherwise you will use the domain name.

| Name                    | Required | Description                                                                                                                                                                         | Default Value         |
| ----------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `API Port`              | Yes      | This is the port of the backend. This is a port not a variable.                                                                                                                     | 8016                  |
| `SECRET_KEY`            | Yes      | Secret Backend Key. Change to anything.                                                                                                                                             | CHANGEME              |
| `PGHOST`                | Yes      | This is how the backend will access the database, use the database containers name.                                                                                                 | PostGIS               |
| `PGDATABASE`            | Yes      | Name of the database in PostGIS to access.                                                                                                                                          | database              |
| `PGUSER`                | Yes      | Name of the User to access with. This is the same as the variable in the database.                                                                                                  | adventure             |
| `PGPASSWORD`            | Yes      | Password of the User it's accessing with. This is the same as the variable in the database.                                                                                         | changeme123           |
| `PGPORT`                | No       | Port to access the database at.                                                                                                                                                     | 5432                  |
| `DJANGO_ADMIN_USERNAME` | Yes      | Default username for admin access.                                                                                                                                                  | admin                 |
| `DJANGO_ADMIN_PASSWORD` | Yes      | Default password for admin access, change after inital login.                                                                                                                       | admin                 |
| `DJANGO_ADMIN_EMAIL`    | Yes      | Default admin user's email. **Note:** You cannot make more than one user with each email.                                                                                           | admin@example.com     |
| `PUBLIC_URL`            | Yes      | This needs to match how you will connect to the backend, so either localhost with matching port or domain. It is used for the creation of image urls.                               | http://localhost:8016 |
| `CSRF_TRUSTED_ORIGINS`  | Yes      | This needs to be changed to the urls of how you connect to your backend server and frontend. These values are comma seperated.                                                      | http://localhost:8016 |
| `FRONTEND_URL`          | Yes      | This needs to match how you will connect to the frontend, so either localhost with matching port or domain. This link should be available for all users. Used for email generation. | http://localhost:8015 |

![/static/img/unraid-config-1.png](/unraid-config-1.png)

## Frontend

- By default, the frontend connects to the backend using `http://server:8000`. This will work if both the frontend and backend are on the same network and the backend is named server. Otherwise, you’ll need to configure it to use the exposed port (default: 8016).

| Name                | Required  | Description                                                                                                                                                   | Default Value         |
| ------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `WEB UI Port`       | Yes       | The port of the frontend. This is not a variable.                                                                                                             | 8015                  |
| `PUBLIC_SERVER_URL` | Yes       | What the frontend SSR server uses to connect to the backend. Change server to the name of the backend container.                                              | http://server:8000    |
| `ORIGIN`            | Sometimes | Set to the URL you will access the frontend from such as localhost with corret port or set it to the domain of what you will acess the app from.              | http://localhost:8015 |
| `BODY_SIZE_LIMIT`   | Yes       | Used to set the maximum upload size to the server. Should be changed to prevent someone from uploading too much! Custom values must be set in **kiliobytes**. | Infinity              |

![/static/img/unraid-config-3.png](/unraid-config-3.png)
