# Change Email Backend

To change the email backend, you can set the following variable in your docker-compose.yml under the server service:

## Using Console (default)

```yaml
environment:
  - EMAIL_BACKEND=console
```

## With SMTP

```yaml
environment:
  - EMAIL_BACKEND=email
  - EMAIL_HOST=smtp.gmail.com
  - EMAIL_USE_TLS=True
  - EMAIL_PORT=587
  - EMAIL_USE_SSL=False
  - EMAIL_HOST_USER=user
  - EMAIL_HOST_PASSWORD=password
  - DEFAULT_FROM_EMAIL=user@example.com
```

## Customizing Emails

By default, the email will display `[example.com]` in the subject. You can customize this in the admin site.

1. Go to the admin site (serverurl/admin)
2. Click on `Sites`
3. Click on first site, it will probably be `example.com`
4. Change the `Domain name` and `Display name` to your desired values
5. Click `Save`
