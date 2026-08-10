#!/bin/sh

if [ -z "${ORIGIN:-}" ] && [ -n "${SITE_URL:-}" ]; then
	export ORIGIN="$SITE_URL"
fi

echo "The origin to be set is: ${ORIGIN:-not set}"
ORIGIN="${ORIGIN:-}" exec node build
