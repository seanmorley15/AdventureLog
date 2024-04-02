#!/bin/sh

# Start your application here
# Example: node build/index.js
# print message
echo "Starting AdventureLog"
npm run migrate
node build/index.js
