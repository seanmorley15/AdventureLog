#!/bin/bash
# Snapshot container environment for cron jobs (cron does not inherit Docker env vars).
set -euo pipefail

mkdir -p /etc/adventurelog /var/log/adventurelog /var/lock
env > /etc/adventurelog/cron.env
chmod 0644 /etc/adventurelog/cron.env
