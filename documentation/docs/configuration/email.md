# Change Email Backend

To change the email backend, you can set the following variable in your docker-compose.yml under the server service:

## Using Console (default)

```yaml
environment:
  - EMAIL_BACKEND='console'
```

## With SMTP

```yaml
environment:
  - EMAIL_BACKEND='email'
  - EMAIL_HOST='smtp.gmail.com'
  - EMAIL_USE_TLS=False
  - EMAIL_PORT=587
  - EMAIL_USE_SSL=True
  - EMAIL_HOST_USER='user'
  - EMAIL_HOST_PASSWORD='password'
  - DEFAULT_FROM_EMAIL='user@example.com'
```
