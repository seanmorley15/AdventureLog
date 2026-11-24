# Umami Analytics

[Umami](https://umami.is/) is an open-source, privacy-focused web analytics tool. AdventureLog can send page views to your Umami site, so you can see how your server is used. It's off unless you set it up.

## Turn it on

1. In Umami, add a website and copy its **Website ID**.
2. Add these to your env file (`.env` for Standard Deployment, `.env.advanced` for Advanced). On Advanced Deployment they belong to the frontend (`web`) service.

   ::: code-group

   ```env [.env]
   PUBLIC_UMAMI_SRC=https://cloud.umami.is/script.js
   PUBLIC_UMAMI_WEBSITE_ID=your_website_id
   ```

   ```yaml [docker-compose.yml]
   environment:
     - PUBLIC_UMAMI_SRC=https://cloud.umami.is/script.js
     - PUBLIC_UMAMI_WEBSITE_ID=your_website_id
   ```

   :::

3. Restart AdventureLog.

| Variable | Description |
| -------- | ----------- |
| `PUBLIC_UMAMI_SRC` | The Umami tracking script. Use `https://cloud.umami.is/script.js` for Umami Cloud, or `https://<your-umami>/script.js` if you host Umami yourself. |
| `PUBLIC_UMAMI_WEBSITE_ID` | The website ID from Umami |

If your users are in the EU or elsewhere with privacy rules, tell them you collect analytics.
