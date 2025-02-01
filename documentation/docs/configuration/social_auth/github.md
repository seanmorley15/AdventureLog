# GitHub Social Authentication

AdventureLog can be configured to use GitHub as an identity provider for social authentication. Users can then log in to AdventureLog using their GitHub account.

# Configuration

To enable GitHub as an identity provider, the administrator must first configure GitHub to allow AdventureLog to authenticate users.

### GitHub Configuration

1. Visit the GitHub OAuth Apps Settings page at [https://github.com/settings/developers](https://github.com/settings/developers).
2. Click on `New OAuth App`.
3. Fill in the following fields:

   - Application Name: `AdventureLog` or any other name you prefer.
   - Homepage URL: `<adventurelog-frontend-url>` where `<adventurelog-frontend-url>` is the URL of your AdventureLog Frontend service.
   - Application Description: `AdventureLog` or any other description you prefer.
   - Authorization callback URL: `http://<adventurelog-backend-url>/accounts/github/login/callback/` where `<adventurelog-backend-url>` is the URL of your AdventureLog Backend service.
   - If you want the logo, you can find it [here](https://adventurelog.app/adventurelog.png).

### AdventureLog Configuration

This configuration is done in the [Admin Panel](../../guides/admin_panel.md). You can either launch the panel directly from the `Settings` page or navigate to `/admin` on your AdventureLog server.

1. Login to AdventureLog as an administrator and navigate to the `Settings` page.
2. Scroll down to the `Administration Settings` and launch the admin panel.
3. In the admin panel, navigate to the `Social Accounts` section and click the add button next to `Social applications`. Fill in the following fields:

   - Provider: `GitHub`
   - Provider ID: GitHub Client ID
   - Name: `GitHub`
   - Client ID: GitHub Client ID
   - Secret Key: GitHub Client Secret
   - Key: can be left blank
   - Settings: can be left blank
   - Sites: move over the sites you want to enable Authentik on, usually `example.com` and `www.example.com` unless you renamed your sites.

#### What it Should Look Like

![Authentik Social Auth Configuration](/github_settings.png)

4. Save the configuration.

Users should now be able to log in to AdventureLog using their GitHub account, and link it to existing accounts.
