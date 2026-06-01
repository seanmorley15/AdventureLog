# API Keys

API keys let you authenticate with AdventureLog's REST API without using a session cookie. This is useful for scripts, integrations, or any programmatic access to your data.

## Creating an API Key

1. Go to **Settings → Security** (or navigate to `/settings?tab=security`)
2. Enter a descriptive name for the key (e.g. `home-automation`, `backup-script`)
3. Click **Create Key**

The full key is displayed **once** immediately after creation. Copy it now — it cannot be retrieved again. Only a prefix (e.g. `al_xxxxxxxx…`) is stored and shown afterward for identification purposes.

## Using an API Key

Include the key in every request using either of these headers:

**Preferred:**

```http
X-API-Key: al_your_key_here
```

**Alternative:**

```http
Authorization: Api-Key al_your_key_here
```

### Example with `curl`

```bash
curl https://your-adventurelog-instance.com/api/adventures/ \
  -H "X-API-Key: al_your_key_here"
```

### Example with Python

```python
import requests

headers = {"X-API-Key": "al_your_key_here"}
response = requests.get("https://your-adventurelog-instance.com/api/locations/", headers=headers)
print(response.json())
```

## Managing Keys

All your keys are listed under **Settings → Security**. Each entry shows:

| Field         | Description                                                 |
| ------------- | ----------------------------------------------------------- |
| **Name**      | The label you gave the key                                  |
| **Prefix**    | Short identifier (e.g. `al_xxxxxxxx…`)                      |
| **Created**   | When the key was generated                                  |
| **Last Used** | The most recent request that used the key (or _Never used_) |

## Revoking a Key

Click **Revoke** next to any key to permanently delete it. Revoked keys stop working immediately. There is no way to restore a revoked key.

## Security Notes

- Raw key values are never stored — only a SHA-256 hash is kept on the server.
- API key requests bypass CSRF checks, so keep your keys secure and treat them like passwords.
- Create separate keys for separate use cases so you can revoke individual access without affecting others.
- If a key is ever exposed, revoke it immediately and generate a new one.
