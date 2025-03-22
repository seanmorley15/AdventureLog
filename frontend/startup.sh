#!/bin/sh

echo "The origin to be set is: $ORIGIN"
# Start the application
ORIGIN=$ORIGIN exec node build
