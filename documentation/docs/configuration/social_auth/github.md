# GitHub

Let people sign in to AdventureLog with their GitHub account. Read [Social Auth & OIDC](../social_auth.md) first for how setup works.

## In GitHub

1. Open [GitHub's developer settings](https://github.com/settings/developers) and choose **New OAuth App**.
2. Fill in:
   - **Application name**: `AdventureLog`, or any name.
   - **Homepage URL**: your AdventureLog address, for example `https://adventurelog.example.com`.
   - **Authorization callback URL**: `https://adventurelog.example.com/accounts/github/login/callback/`, using your backend's public address (`SITE_URL` on Standard Deployment, `PUBLIC_URL` on Advanced).
3. Register the app, generate a client secret, and copy the **Client ID** and **Client Secret**. The [AdventureLog logo](https://adventurelog.app/adventurelog.png) is available for the app icon.

## In AdventureLog

In the [Admin Panel](../../guides/admin_panel.md), go to **Social Accounts → Social applications → Add**:

| Field | Value |
| ----- | ----- |
| Provider | `GitHub` |
| Provider ID | The GitHub client ID |
| Name | `GitHub` |
| Client ID | The GitHub client ID |
| Secret key | The GitHub client secret |
| Key, Settings | Leave blank |
| Sites | Move your site to **Chosen sites** |

![GitHub social application settings in the AdventureLog admin panel](/github_settings.png)

Save. **GitHub** now appears on the login page.
