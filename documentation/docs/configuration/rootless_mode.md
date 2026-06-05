# Rootless Mode

To enable rootless mode, you must:

- set a non-root user to run the container (any UID will work)
- update ownership of media volume (mounted as `/code/media/`) to your selected UID
- set the following environment variable for server service

```yaml
environment:
  - LOG_FILE=/tmp/scheduler.log
```
