---
sidebar_position: 1
---

# Updating

Updating AdventureLog when using docker can be quite easy. Run the folowing commands to pull the latest version and restart the containers. Make sure you backup your instance before updating just in case!

Note: Make sure you are in the same directory as your `docker-compose.yml` file.

```bash
docker compose pull
docker compose up -d
```

## Updating the Region Data

Region and Country data in AdventureLog is provided by an open source project: [dr5hn/countries-states-cities-database](https://github.com/dr5hn/countries-states-cities-database). If you would like to update the region data in your AdventureLog instance, you can do so by running the following command. This will make sure your database is up to date with the latest region data for your version of AdventureLog. For security reasons, the region data is not automatically updated to the latest and is release version is controlled in the `settings.py` file.

```bash
docker exec -it <container> bash
```

Once you are in the container run the following command to resync the region data.

```bash
python manage.py download-countries
```
