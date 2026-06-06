#!/bin/bash
set -euo pipefail

source /aio/env-setup.sh

cd /code
source /code/scripts/entrypoint-common.sh

wait_for_postgres
run_migrations
create_superuser_if_needed
run_download_countries
finalize_startup

exec "$@"
