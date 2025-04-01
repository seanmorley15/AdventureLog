#!/bin/bash

# Any setup tasks or checks can go here (if needed)
echo "AdventureLog CDN has started!"
echo "Refer to the documentation for information about connecting your AdventureLog instance to this CDN."
echo "Thanks to our data providers for making this possible! You can find them on the CDN site."

# Start Nginx in the foreground (as the main process)
nginx -g 'daemon off;'
