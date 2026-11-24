# Disable Registration

To disable registration, set the following variables in your `.env` file, or under the server service in your compose file:

::: code-group

```env [.env]
DISABLE_REGISTRATION=True
# OPTIONAL: the message shown when registration is disabled
DISABLE_REGISTRATION_MESSAGE='Registration is disabled for this instance of AdventureLog.'
```

```yaml [docker-compose.yml]
environment:
  - DISABLE_REGISTRATION=True
  # OPTIONAL: the message shown when registration is disabled
  - DISABLE_REGISTRATION_MESSAGE='Registration is disabled for this instance of AdventureLog.'
```

:::
