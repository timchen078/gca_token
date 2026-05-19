# GCA Email Registration Backend

This is the deployed backend package for the public GCA email registration form.

The public website remains hosted on GitHub Pages. The write API is deployed on Cloudflare Workers + D1 and currently exposed as:

```text
https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations
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

## Deployed Cloudflare Resources

- Worker: `gca-registration-api`
- Workers.dev endpoint: `https://gca-registration-api.gcagochina.workers.dev`
- D1 database: `gca_registration`
- D1 database id: `b4cb13f7-c52e-4dbc-b8d6-50346a814819`
- Public site integration: `site/register.html`

The future custom domain `api.gcagochina.com` still requires `gcagochina.com` to be moved into Cloudflare DNS or added to the same Cloudflare account as a proxied zone.

## Deployment Commands

Run these commands from `cloudflare/gca-registration-worker/` after logging in to the correct Cloudflare account:

```bash
npm install
npx wrangler d1 create gca_registration
```

Copy the returned D1 `database_id` into `wrangler.toml`.

Then apply the migration and set required secrets:

```bash
npx wrangler d1 migrations apply gca_registration --remote
npx wrangler secret put ADMIN_READ_TOKEN
npx wrangler secret put PRIVACY_HASH_SALT
npx wrangler deploy
```

The current configuration publishes through `workers.dev`. Switch to a Cloudflare custom domain only after the official domain is managed by Cloudflare.

## Smoke Test

```bash
curl -fsS https://gca-registration-api.gcagochina.workers.dev/health

curl -fsS https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations \
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

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"
```

## Current Public Site Behavior

`site/register.html` now tries the production Workers API first when loaded from `gcagochina.com`. If the API temporarily fails, the page exposes the official email fallback to avoid losing user registrations.
