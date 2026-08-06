# S3 Media Storage

Store AdventureLog user uploads (images, attachments) on S3-compatible object storage instead of the local filesystem. Supported providers include AWS S3, Cloudflare R2, DigitalOcean Spaces, and MinIO.

### Recommendation

- Choose storage (local or S3) at install time. Migrating an existing instance from local filesystem storage to S3 (or vice-versa) is complex and error-prone. If you already run a production instance with media on local storage, prefer configuring a new instance to use S3 rather than attempting an in-place migration.

### How it works

AdventureLog can be configured to use an S3-compatible backend (AWS S3, Cloudflare R2, DigitalOcean Spaces, MinIO, etc.). When enabled, uploads are stored in the configured bucket and the app generates public or signed URLs for access depending on configuration.

### Minimum `.env` settings

Add the following variables to your `.env` to enable S3 storage (adjust values to your provider):

```
# Enable S3-compatible media storage
MEDIA_STORAGE=s3

# Optional: limit storage (0 = unlimited)
MEDIA_STORAGE_LIMIT_MB=0

# Credentials and bucket
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_STORAGE_BUCKET_NAME=your_bucket_name

# Endpoint and region (Cloudflare R2 or other providers)
AWS_S3_ENDPOINT_URL=                       # e.g. https://<account>.r2.cloudflarestorage.com
AWS_S3_REGION_NAME=auto
AWS_S3_ADDRESSING_STYLE=path
AWS_S3_SIGNATURE_VERSION=s3v4

# Optional CDN/custom domain
AWS_S3_CUSTOM_DOMAIN=                      # e.g. media.example.com

# URL signing and expiry
AWS_QUERYSTRING_AUTH=true
AWS_QUERYSTRING_EXPIRE=3600

# File overwrite behavior
AWS_S3_FILE_OVERWRITE=true
```

Notes:

- For AWS use the normal S3 endpoint (leave `AWS_S3_ENDPOINT_URL` empty). For R2/MinIO/Spaces set the provider endpoint.
- `AWS_S3_CUSTOM_DOMAIN` should point to a CDN or domain that proxies to the bucket (configure DNS/CNAME accordingly).
- If you set `AWS_QUERYSTRING_AUTH=false` and use a public CDN, files will be publicly accessible — ensure that aligns with your privacy needs.

### Cloudflare R2 example

```
AWS_ACCESS_KEY_ID=abcd...
AWS_SECRET_ACCESS_KEY=xyz...
AWS_STORAGE_BUCKET_NAME=my-bucket
AWS_S3_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com
AWS_S3_REGION_NAME=auto
```

### Testing and staging

- Configure S3 on a staging or new instance first. Verify uploads, thumbnails, and public URL generation before switching production traffic.
- Uploads should appear in the configured bucket and image preview endpoints should return correct Content-Type and caching headers.

### Migration guidance (local → S3)

Migrating existing files from local disk to S3 requires copying all media objects to the bucket and updating any references/paths stored in the database. Typical steps:

1. Create and configure the target S3 bucket and credentials.
2. Copy files from the `media/` (or configured) directory into the bucket, preserving paths. For example, using `aws s3 sync` or `s3cmd`:

```bash
# example using AWS CLI
aws s3 sync /path/to/local/media s3://your_bucket --acl private --endpoint-url https://<endpoint>
```

3. Ensure the app's `MEDIA_STORAGE` and S3 env vars are set and the staging app can read objects correctly.
4. Update any references if your system stored absolute local paths (most setups store relative paths and will work if the bucket mirrors the path layout).
5. Run thorough tests (user uploads, thumbnails, public access, downloads). Expect possible downtime while switching if paths/URLs change.

Because of these complexities, we recommend enabling S3 on a fresh instance or planning migration carefully (backups, verification, and possibly a short maintenance window).

### Troubleshooting

- Access denied errors: check access keys, bucket policy, and `AWS_S3_ENDPOINT_URL` (for non-AWS providers).
- Missing objects after sync: verify paths preserved and no prefix issues (e.g., leading slashes).
- Incorrect content type: ensure the upload client sets correct Content-Type or add a sync step to set metadata.
