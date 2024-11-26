# Troubleshooting: Images Not Displayed in AdventureLog

The AdventureLog backend container uses a built-in Nginx container to serve media to the frontend. The `PUBLIC_URL` environment variable is set to the external URL of the **backend** container. This URL is used to generate the URLs for the images in the frontend. If this URL is not set correctly or not accessible from the frontend, the images will not be displayed.

If you're experiencing issues with images not displaying in AdventureLog, follow these troubleshooting steps to resolve the issue.

1. **Check the `PUBLIC_URL` Environment Variable**:

   - Verify that the `PUBLIC_URL` environment variable is set correctly in the `docker-compose.yml` file for the `server` service.
   - The `PUBLIC_URL` should be set to the external URL of the backend container. For example:
     ```
     PUBLIC_URL=http://backend.example.com
     ```

2. **Check `CSRF_TRUSTED_ORIGINS` Environment Variable**:
   - If you have set the `CSRF_TRUSTED_ORIGINS` environment variable in the `docker-compose.yml` file, ensure that it includes the frontend URL and the backend URL.
   - For example:
     ```
     CSRF_TRUSTED_ORIGINS=http://frontend.example.com,http://backend.example.com
     ```
