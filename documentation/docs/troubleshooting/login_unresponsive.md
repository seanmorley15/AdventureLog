# Troubleshooting: Login and Registration Unresponsive

When you encounter issues with the login and registration pages being unresponsive in AdventureLog, it can be due to various reasons. This guide will help you troubleshoot and resolve the unresponsive login and registration pages in AdventureLog.

1. Check to make sure the backend container is running and accessible.

   - Check the backend container logs to see if there are any errors or issues blocking the contianer from running.

2. Check the connection between the frontend and backend containers.

   - Attempt login with the browser console network tab open to see if there are any errors or issues with the connection between the frontend and backend containers. If there is a connection issue, the code will show an error like `Failed to load resource: net::ERR_CONNECTION_REFUSED`. If this is the case, check the `PUBLIC_SERVER_URL` in the frontend container and refer to the installation docs to ensure the correct URL is set.
   - If the error is `403`, continue to the next step.

3. The error most likely is due to a CSRF security config issue in either the backend or frontend.

   - Check that the `ORIGIN` variable in the frontend is set to the URL where the frontend is access and you are accessing the app from currently.
   - Check that the `CSRF_TRUSTED_ORIGINS` variable in the backend is set to a comma separated list of the origins where you use your backend server and frontend. One of these values should match the `ORIGIN` variable in the frontend.

4. If you are still experiencing issues, please refer to the [AdventureLog Discord Server](https://discord.gg/wRbQ9Egr8C) for further assistance, providing as much detail as possible about the issue you are experiencing!
