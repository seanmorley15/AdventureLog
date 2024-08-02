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

Region data in AdventureLog is stored in a seeding file. This file can change and there is an easy command to resync the region data without needing any database changes. This can be run by acessing the contianers terminal as follows.

```bash
docker exec -it <container> bash
```

Once you are in the container run the following command to resync the region data.

```bash
python manage.py worldtravel-seed --force
```
