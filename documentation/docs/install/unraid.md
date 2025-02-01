# Installation with Unraid

AdventureLog is available in the Unraid Community Applications store. You can install it by searching for `AdventureLog` in the Community Applications store, where you will find the frontend and the backend. The database can be found by searching `PostGIS`.

Community Applications Page for AdventureLog: [AdventureLog on CA Store](https://unraid.net/community/apps?q=AdventureLog)\
Community Applications Page for PostGIS: [PostGIS on CA Store](https://unraid.net/community/apps?q=PostGIS)

## Installation Configuration

- **Note:** It is recommended to install the applications in the order of these instructions, as failing to do so could cause issues.\
- Container names can be set to whatever you desire.
- Also ensure they are all on the same custom network so they can communicate with one another. You can create one by running the following command in your command line, with `example` being set to your desired name. This network will then show up for selection when making the apps/containers.

```bash
docker network create example
```

## Database

- Network type should be set to your **custom network**.
- There is **no** AdventureLog---Database app, to find the database application search for `PostGIS` on the Unraid App Store then add and fill out the fields as shown below
- Change the repository version to `postgis/postgis:15-3.3`
- Ensure that the variables ```POSTGRES_DB```, ```POSTGRES_USER```, and ```POSTGRES_PASSWORD``` are set in the ```PostGIS``` container. If not, then add them as custom variables. The template should have ```POSTGRES_PASSWORD``` already and you will simply have to add ```POSTGRES_DB``` and ```POSTGRES_USER```.
- The forwarded port of ```5012``` is not needed unless you plan to access the database outside of the container's network.

| Name                | Required | Description                                                                      | Default Value   |
| ------------------- | -------- | -------------------------------------------------------------------------------- | --------------- |
| `POSTGRES_DB`       | Yes      | The name of the database in PostGIS.                                             | `N/A`           |
| `POSTGRES_USER`     | Yes      | Name of the user generated on first start that will have access to the database. | `N/A`           |
| `POSTGRES_PASSWORD` | Yes      | Password of the user that will be generated on first start.                      | `N/A`           |

- Here's some visual instructions of how to configure the database template, click the image to open larger version in new tab.\
[![/static/img/unraid-config-2.png](/unraid-config-2.png)](/unraid-config-2.png)

## Backend

- Network type should be set to your **custom network**.
- **Note:** If you're running the server in a docker network that is other than "host" (for example "bridge"), then you need to add the IP of the host machine in the CSRF Trusted Origins variable instead of using localhost. This is only necessary when accessing locally, otherwise you will use the domain name.

| Name                    | Required | Description                                                                                                                                                                         | Default Value                                   |
| ----------------------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `API Port`              | Yes      | This is the port of the backend. This is a port, not a variable.                                                                                                                    | `8016`                                          |
| `PGHOST`                | Yes      | This is how the backend will access the database. Use the database container's name.                                                                                                | `N/A`                                           |
| `PGDATABASE`            | Yes      | Name of the database in PostGIS to access.                                                                                                                                          | `N/A`                                           |
| `PGUSER`                | Yes      | Name of the user to access with. This is the same as the variable in the database.                                                                                                  | `N/A`                                           |
| `PGPASSWORD`            | Yes      | Password of the user it's accessing with. This is the same as the variable in the database.                                                                                         | `N/A`                                           |
| `SECRET_KEY`            | Yes      | Secret Backend Key. Change to anything.                                                                                                                                             | `N/A`                                           |
| `DJANGO_ADMIN_USERNAME` | Yes      | Default username for admin access.                                                                                                                                                  | `admin`                                         |
| `DJANGO_ADMIN_EMAIL`    | Yes      | Default admin user's email. **Note:** You cannot make more than one user with each email.                                                                                           | `N/A`                                           |
| `DJANGO_ADMIN_PASSWORD` | Yes      | Default password for admin access. Change after initial login.                                                                                                                      | `N/A`                                           |
| `PUBLIC_URL`            | Yes      | This needs to match how you will connect to the backend, so either local ip with matching port or domain. It is used for the creation of image URLs.                                | `http://IP_ADDRESS:8016`                        |
| `FRONTEND_URL`          | Yes      | This needs to match how you will connect to the frontend, so either local ip with matching port or domain. This link should be available for all users. Used for email generation.  | `http://IP_ADDRESS:8015`                        |
| `CSRF_TRUSTED_ORIGINS`  | Yes      | This needs to be changed to the URLs of how you connect to your backend server and frontend. These values are comma-separated and usually the same as the 2 above values.           | `http://IP_ADDRESS:8016,http://IP_ADDRESS:8015` |

- Here's some visual instructions of how to configure the backend template, click the image to open larger version in new tab.\
[![static/img/unraid-config-1.png](/unraid-config-1.png)](/unraid-config-1.png)

## Frontend

- Network type should be set to your **custom network**.
- **Note:** The default value for ```PUBLIC_SERVER_URL``` is ```http://IP_ADDRESS:8000```, however ```IP_ADDRESS``` **should be changed** to the name of the backend container for simplicity.

| Name                | Required | Description                                                                                                                                                  | Default Value            |
| ------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| `WEB UI Port`       | Yes      | The port of the frontend. This is not a variable.                                                                                                            | `8015`                   |
| `PUBLIC_SERVER_URL` | Yes      | What the frontend SSR server uses to connect to the backend. Change `IP_ADDRESS` to the name of the backend container.                                       | `http://IP_ADDRESS:8000` |
| `ORIGIN`            | Sometimes| Set to the URL you will access the frontend from, such as localhost with correct port, or set it to the domain of what you will access the app from.         | `http://IP_ADDRESS:8015` |
| `BODY_SIZE_LIMIT`   | Yes      | Used to set the maximum upload size to the server. Should be changed to prevent someone from uploading too much! Custom values must be set in **kilobytes**. | `Infinity`               |

- Here's some visual instructions of how to configure the frontend template, click the image to open larger version in new tab.\
[![/static/img/unraid-config-3.png](/unraid-config-3.png)](/unraid-config-3.png)
