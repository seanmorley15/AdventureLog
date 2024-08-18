docker run --rm \
  -v adventurelog_adventurelog_media:/backup-volume \
  -v "$(pwd)":/backup \
  busybox \
  tar -zcvf /backup/adventurelog-backup.tar.gz /backup-volume