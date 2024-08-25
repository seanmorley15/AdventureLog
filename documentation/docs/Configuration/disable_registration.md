---
sidebar_position: 1
---

# Disable Registration

To disable registration, you can set the following variable in your docker-compose.yml under the server service:

```yaml
environment:
  - DISABLE_REGISTRATION=True
  # OPTIONAL: Set the message to display when registration is disabled
  - DISABLE_REGISTRATION_MESSAGE='Registration is disabled for this instance of AdventureLog.'
```
