# GCA Email Registration Backend

This is the production-ready backend package for the public GCA email registration form.

The public website remains hosted on GitHub Pages. The write API should be deployed separately on Cloudflare Worker + D1 and exposed as:

```text
https://api.gcagochina.com/gca/email-registrations
```

## What It Stores

- email
- optional display name
- registration source and language
- interest tags
- contact-consent acknowledgement
- no-secrets/no-custody acknowledgement
- generated `emailRegistrationId`
- timestamps
- optional salted IP hash if `PRIVACY_HASH_SALT` is configured

It does not collect wallet private keys, seed phrases, wallet passwords, exchange API secrets, withdrawal permissions, one-time codes, or remote-control access. It does not transfer GCA, activate credits, or activate GCA Member status.

## Deploy Steps

Run these commands from `cloudflare/gca-registration-worker/` after logging in to the correct Cloudflare account:

```bash
npm install
npx wrangler d1 create gca_registration
```

Copy the returned D1 `database_id` into `wrangler.toml`, replacing `REPLACE_WITH_CLOUDFLARE_D1_DATABASE_ID`.

Then apply the migration and set required secrets:

```bash
npx wrangler d1 migrations apply gca_registration --remote
npx wrangler secret put ADMIN_READ_TOKEN
npx wrangler secret put PRIVACY_HASH_SALT
npx wrangler deploy
```

After deployment, attach the Worker to `api.gcagochina.com` in Cloudflare Workers routes or custom domains.

## Smoke Test

```bash
curl -fsS https://api.gcagochina.com/health

curl -fsS https://api.gcagochina.com/gca/email-registrations \
  -H 'content-type: application/json' \
  -X POST \
  --data '{
    "packetVersion": "gca_email_registration_v1",
    "email": "user@example.com",
    "source": "register.html",
    "language": "zh-CN",
    "interests": ["gca_updates", "member_access"],
    "acknowledgements": {
      "emailContactConsent": true,
      "noSecretsNoCustody": true
    }
  }'

curl -fsS 'https://api.gcagochina.com/gca/email-registrations?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"
```

## Current Public Site Behavior

`site/register.html` now tries the production API first when loaded from `gcagochina.com`. If the API is not deployed or temporarily fails, the page exposes the official email fallback to avoid losing user registrations.
