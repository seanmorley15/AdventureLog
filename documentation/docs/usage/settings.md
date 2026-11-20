# Account and Settings

Open **Settings** from the menu under your avatar. The tabs on the left cover your profile, sign-in, connected apps, and your data. Language and theme are in the same avatar menu.

## Profile

- **Personal information**: your username, first and last name, and profile picture.
- **Profile visibility**: who can see your profile and find you to share collections.

  | Setting | Who can see you |
  | ------- | --------------- |
  | **Private** | Only you. Nobody can find you to share a collection. Choosing this removes you from collections shared with you and cancels pending invites. |
  | **Signed-in users** | Everyone signed in to this server, who can also invite you to collections |
  | **Public** | Anyone, including visitors who aren't signed in. Unavailable when the server [turns off public access](../configuration/public_access.md). |

- **Preferences**: your date format, the currency that pre-fills money fields, the default map style, and metric or imperial units.

## Emails

Add email addresses, verify them, and choose the primary one. AdventureLog sends invitations, password resets, and notifications to the primary address. A verified address is needed to turn on multi-factor authentication.

## Security

| Section | What you can do |
| ------- | --------------- |
| **Change Password** | Set a new password. You're signed out afterward. |
| **Active Sessions** | See every device you're signed in on, and sign out the ones you don't recognize, or all others at once. |
| **Multi-Factor Authentication** | Require a code from an authenticator app when you sign in. Scan the QR code to set it up. |
| **Sign-in Methods** | Link an account from an identity provider, such as Authentik or GitHub, with **Launch Account Connections**. The providers come from the server admin; see [Social Auth & OIDC](../configuration/social_auth.md). |
| **API Keys** | Create keys for scripts and other apps. A key is shown once, when you create it. See [API Keys](../configuration/api_keys.md). |

## Integrations

Connect other apps to your account. Each user connects their own.

| App | What it adds |
| --- | ------------ |
| [Immich](../configuration/immich_integration.md) | Pick photos from your Immich library for a location |
| [Strava](../configuration/strava_integration.md) | Import activities into visits. The server admin must turn it on first. |
| [Endurain](../configuration/endurain_integration.md) | Import activities and their GPS tracks into visits |
| [Wanderer](../configuration/wanderer_integration.md) | Link trails to locations |
| [Google Maps](../configuration/google_maps_integration.md) | Shown as on or off. The server admin sets it up for everyone. |

## Data and Storage {#data-and-storage}

- **Media Storage** shows how much space your photos, attachments, and profile picture use, and your limit if the server sets one.
- **Backup Your Data** downloads one file with your whole account: locations, visits, collections, media, profile, and integration settings. Large accounts take a while; the button shows progress and the download starts when the file is ready.
- **Restore Data** uploads a backup file. **It replaces everything in your account**, so you have to confirm first.

Use an account backup to move your account to another AdventureLog server, or to keep your own copy. To move a single trip instead, export the collection; see [Trips and Collections](trips.md#exporting-and-importing-a-collection). Server admins back up the whole server separately; see [Backups and Restore](../configuration/backups.md).

## Danger Zone

**Delete Account** permanently removes your account and everything in it: locations, collections, media, integrations, and settings. You confirm with your username and password. Staff accounts can't be deleted here; another admin removes staff status first, or deletes the account from the admin panel.

## About

Your account details, including whether you're staff, and the AdventureLog version the server runs.

## Admin

Only staff see this tab. It opens the [Admin Panel](../guides/admin_panel.md), and **Update Visited Regions** marks the regions and cities of your locations as visited right away instead of waiting for the nightly update.
