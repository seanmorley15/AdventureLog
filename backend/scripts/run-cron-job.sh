#!/bin/bash
# Run a Django management command as a cron job with logging and overlap protection.
#
# Usage:
#   run-cron-job.sh <job-name> <manage.py-command> [command-args...]
#
# Output goes to /var/log/adventurelog/<job-name>.log and Docker logs (via PID 1 stdout).

set -euo pipefail

JOB_NAME="${1:?job name required}"
shift

cd /code

LOCK_FILE="/var/lock/adventurelog-${JOB_NAME}.lock"
LOG_DIR="/var/log/adventurelog"
LOG_FILE="${LOG_DIR}/${JOB_NAME}.log"
mkdir -p "$LOG_DIR"

log() {
	printf '[cron:%s] %s\n' "$JOB_NAME" "$*" >>/proc/1/fd/1 2>/dev/null || \
		printf '[cron:%s] %s\n' "$JOB_NAME" "$*"
}

# Cron runs with a minimal environment; load the snapshot written at container start.
if [[ -f /etc/adventurelog/cron.env ]]; then
	set -a
	# shellcheck disable=SC1091
	source /etc/adventurelog/cron.env
	set +a
else
	log "WARNING: /etc/adventurelog/cron.env missing — Django may fail to connect to the database"
fi

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
	log "Skipped — previous run still in progress"
	exit 0
fi

log "Starting manage.py $*"

set +e
/usr/local/bin/python3 manage.py "$@" 2>&1 | tee -a "$LOG_FILE" >>/proc/1/fd/1
exit_code=${PIPESTATUS[0]}
set -e

if [[ "$exit_code" -ne 0 ]]; then
	log "Failed with exit code ${exit_code}. See ${LOG_FILE}"
	exit "$exit_code"
fi

log "Finished manage.py $*"
