---
sidebar_position: 2
---

# AdventureLog v0.7.1 Migration Guide

In order to make installation easier, the AdventureLog v0.7.1 release has **removed the need for a seperate nginx container** and cofig to serve the media files. Instead, the media files are now served by an instance of nginx running in the same container as the Django application.

## Docker Compose Changes

:::note

You can also just use the new `docker-compose.yml` file in the repository and change the environment variables to match your setup.

:::

1. Remove the `nginx` service from your `docker-compose.yml` file.
2. Update the `PUBLIC_URL` environment variable in the `server` service (backend) to match the address of your **server**, instead of the previous nginx instance. For example, if your server is exposed to `https://localhost:8000`, set `PUBLIC_URL` to `http://localhost:8000`. If you are using a domain name, set `PUBLIC_URL` to `https://api.yourdomain.com` as an example.
3. Change port mapping for the `server` service. Right now it probably looks like this:
   ```yaml
   ports:
     - "your-exposed-port:8000"
   ```
   Change it to:
   ```yaml
   ports:
     - "your-exposed-port:80"
   ```
   This is because the nginx instance in the container is now serving the Django application on port 80. The port on the left side of the colon is the port on your host machine and this can be changed to whatever you want. The port on the right side of the colon is the port the Django application is running on in the container and should not be changed.

That's it! You should now be able to run the application with the new configuration! This update also includes some performance enhancements so there should be a slight speed increase as well, especially with multiple users.

Enjoy the new version of AdventureLog! 🎉

Report any bugs [GitHub repository](https://github.com/seanmorley15/adventurelog) or ask for help in the [Discord server](https://discord.gg/wRbQ9Egr8C).
