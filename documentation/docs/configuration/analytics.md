# Umami Analytics (optional)

Umami Analytics is a free, open-source, and privacy-focused web analytics tool that can be used as an alternative to Google Analytics. Learn more about Umami Analytics [here](https://umami.is/).

To enable Umami Analytics for your AdventureLog instance, you can set the following variables in your `docker-compose.yml` under the `web` service:

```yaml
PUBLIC_UMAMI_SRC=https://cloud.umami.is/script.js # If you are using the hosted version of Umami
PUBLIC_UMAMI_WEBSITE_ID=
```
