# Endurain

[Endurain](https://docs.endurain.com/) is a self-hosted fitness tracker. Connect it to import your Endurain activities into the visits of your locations, GPS track included.

**Who sets it up:** each user connects their own Endurain account. The server admin doesn't need to do anything.

## Connect your account

1. Go to **Settings → Integrations → Endurain**.
2. Enter your Endurain **Server URL**, for example `https://endurain.example.com`, and your Endurain username and password.
3. Choose **Connect with password**. If your Endurain account uses multi-factor authentication, enter the code when asked.

AdventureLog's server connects to Endurain, so use an address that server can reach, preferably over HTTPS. `localhost` and `127.0.0.1` usually don't work in Docker.

AdventureLog doesn't keep your password. It stores sign-in tokens on the server, refreshes them on its own, and never sends them to your browser. Endurain API keys can't read activities, which is why a password sign-in is used.

## Use it

1. Open a location and add or edit a visit with dates.
2. Choose **Endurain activities** on the visit.
3. Import an activity. AdventureLog fetches its GPS track from Endurain and attaches it to the visit as a GPX file.

## Troubleshooting

| Problem | Fix |
| ------- | --- |
| Can't connect | Check the URL and that the AdventureLog server can reach it. See [An integration can't connect](../troubleshooting/common_issues.md#an-integration-can-t-connect). |
| Activities stop loading | The Endurain session was revoked. Disconnect and connect again in **Settings → Integrations**. |

For how the sign-in works, see Endurain's [authentication guide](https://docs.endurain.com/developer-guide/authentication/).
