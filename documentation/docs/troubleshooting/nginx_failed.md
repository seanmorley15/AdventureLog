# Troubleshooting: `Starting nginx: nginx failed!` in the Backend Container

The AdventureLog backend container uses a built-in Nginx container with a built-in nginx config that relies on the name `server` to be the service name of the backend container. If the Nginx service fails to start in the backend container, the whole backend service will keep restarting and fail to start.

**The primary reason for this error is changing the backend service name `server` to something different**

If you're experiencing issues with the Nginx service failing to start in the backend container, follow these troubleshooting steps to resolve the issue.

### 1. **Check the `server` Service Name**:

- Verify that the service name of the backend container is set to `server` in the `docker-compose.yml` file.
- The service name should be set to `server` in the `docker-compose.yml` file. For example:
  ```yaml
  server:
    image: ghcr.io/seanmorley15/adventurelog-backend:latest
    container_name: adventurelog-backend
  ```

### 2. **To keep the backend service name different**:

- If you want to keep the backend service name different from `server`, you can mount a custom Nginx configuration file to the backend container.

  - Get the default Nginx configuration file from the AdventureLog repository:

  ```bash
  wget https://raw.githubusercontent.com/seanmorley15/AdventureLog/refs/heads/main/backend/nginx.conf
  ```

  - Update the `nginx.conf` file to replace all occurrences of `server` with your custom service name.
  - Mount the custom Nginx configuration file to the backend container in the `docker-compose.yml` file. For example:
    ```yaml
    server:
      image: ghcr.io/seanmorley15/adventurelog-backend:latest
      container_name: adventurelog-backend
      volumes:
        - ./nginx.conf:/etc/nginx/nginx.conf
    ```

### 3. **Restart the Backend Container**:

These steps should help you resolve the issue with the Nginx service failing to start in the backend container. If you continue to face issues, please reach out to the AdventureLog community on Discord or GitHub for further assistance.
