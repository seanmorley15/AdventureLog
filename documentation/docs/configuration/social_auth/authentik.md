# Authentik OIDC Authentication

<img src="https://repository-images.githubusercontent.com/230885748/19f01d00-8e26-11eb-9a14-cf0d28a1b68d" alt="Authentik Logo" width="400" />

Authentik is a self-hosted identity provider that supports OpenID Connect and OAuth2. AdventureLog can be configured to use Authentik as an identity provider for social authentication. Learn more about Authentik at [goauthentik.io](https://goauthentik.io/).

Once Authentik is configured by the administrator, users can log in to AdventureLog using their Authentik account and link existing AdventureLog accounts to Authentik for easier access.

# Configuration

To enable Authentik as an identity provider, the administrator must first configure Authentik to allow AdventureLog to authenticate users.

### Authentik Configuration

1. Log in to Authentik and navigate to the `Providers` page and create a new provider.
2. Select `OAuth2/OpenID Provider` as the provider type.
3. Name it `AdventureLog` or any other name you prefer.
4. Set the `Redirect URI` of type `Regex` to `^http://<adventurelog-server-url>/accounts/oidc/.*$` where `<adventurelog-url>` is the URL of your AdventureLog Server service.
5. Copy the `Client ID` and `Client Secret` generated by Authentik, you will need these to configure AdventureLog.
6. Create an application in Authentik and assign the provider to it, name the `slug` `adventurelog` or any other name you prefer.
7. If you want the logo, you can find it [here](https://adventurelog.app/adventurelog.png).

### AdventureLog Configuration

This configuration is done in the [Admin Panel](../../guides/admin_panel.md). You can either launch the panel directly from the `Settings` page or navigate to `/admin` on your AdventureLog server.

1. Login to AdventureLog as an administrator and navigate to the `Settings` page.
2. Scroll down to the `Administration Settings` and launch the admin panel.
3. In the admin panel, navigate to the `Social Accounts` section and click the add button next to `Social applications`. Fill in the following fields:

   - Provider: `OpenID Connect`
   - Provider ID: Authentik Client ID
   - Name: `Authentik`
   - Client ID: Authentik Client ID
   - Secret Key: Authentik Client Secret
   - Key: can be left blank
   - Settings: (make sure http/https is set correctly)

   ```json
   {
     "server_url": "http://<authentik_url>/application/o/[YOUR_SLUG]/"
   }
   ```

   ::: warning
   `localhost` is most likely not a valid `server_url` for Authentik in this instance because `localhost` is the server running AdventureLog, not Authentik. You should use the IP address of the server running Authentik or the domain name if you have one.

- Sites: move over the sites you want to enable Authentik on, usually `example.com` and `www.example.com` unless you renamed your sites.

#### What it Should Look Like

![Authentik Social Auth Configuration](/authentik_settings.png)

4. Save the configuration.

Ensure that the Authentik server is running and accessible by AdventureLog. Users should now be able to log in to AdventureLog using their Authentik account.

## Linking to Existing Account

If a user has an existing AdventureLog account and wants to link it to their Authentik account, they can do so by logging in to their AdventureLog account and navigating to the `Settings` page. There is a button that says `Launch Account Connections`, click that and then choose the provider to link to the existing account.

## Troubleshooting

### 404 error when logging in.

Ensure the `<adventurelog-server-url>/accounts` path is routed to the backend, as it shouldn't hit the frontend when it's properly configured.

### Authentik - No Permission

In the Authentik instance, check access to the AdventureLog application from a specific user by using the Check Access/Test button on the Application dashboard. If the user doesn't have access, you can add an existing user/group policy to give your specific user/group access to the AdventureLog application.
