# This script will create a backup of the adventurelog_media volume and store it in the current directory as adventurelog-backup.tar.gz

docker run --rm \
  -v adventurelog_adventurelog_media:/backup-volume \
  -v "$(pwd)":/backup \
  busybox \
  tar -zcvf /backup/adventurelog-backup.tar.gz /backup-volume