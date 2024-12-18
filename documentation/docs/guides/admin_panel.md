# AdventureLog Admin Panel

The AdventureLog Admin Panel, powered by Django, is a web-based interface that allows administrators to manage objects in the AdventureLog database. The Admin Panel is accessible at the `/admin` endpoint of the AdventureLog server. Example: `https://al-server.yourdomain.com/admin`.

Features of the Admin Panel include:

- **User Management**: Administrators can view and manage user accounts, including creating new users, updating user information, and deleting users.
- **Adventure Management**: Administrators can view and manage adventures, including creating new adventures, updating adventure information, and deleting adventures.
- **Security**: The Admin Panel enforces access control to ensure that only authorized administrators can access and manage the database. This means that only users with the `is_staff` flag set to `True` can access the Admin Panel.

Note: the `CSRF_TRUSTED_ORIGINS` setting in your `docker-compose.yml` file must include the domain of the server. For example, if your server is hosted at `https://al-server.yourdomain.com`, you should add `al-server.yourdomain.com` to the `CSRF_TRUSTED_ORIGINS` setting.
