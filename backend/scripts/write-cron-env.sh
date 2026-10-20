#!/bin/bash
# Snapshot container environment for cron jobs (cron does not inherit Docker env vars).
set -euo pipefail

mkdir -p /etc/adventurelog /var/log/adventurelog /var/lock
# The snapshot holds secrets (SECRET_KEY, database password); only root, which runs cron, reads it.
(umask 077 && env > /etc/adventurelog/cron.env)
chmod 0600 /etc/adventurelog/cron.env
