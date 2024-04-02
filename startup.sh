#!/bin/sh

# Start your application here
# Example: node build/index.js
# print message
echo "Starting the application"
npm run migrate
node build/index.js
