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
- Admin read endpoint: `GET /gca/email-registrations`
- Admin read secret: configured in Cloudflare as `ADMIN_READ_TOKEN`
- Privacy hash salt: configured in Cloudflare as `PRIVACY_HASH_SALT`

The future custom domain `api.gcagochina.com` still requires Wrangler to be logged into a Cloudflare account that can see the `gcagochina.com` zone. DNS currently uses Cloudflare nameservers, but the currently authorized account does not contain that zone, so Cloudflare rejects the custom-domain deployment with `The zone "gcagochina.com" does not exist on your account`.

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

## Admin Read

The admin read endpoint is enabled by the deployed Worker but protected by `ADMIN_READ_TOKEN`.

The local operator copy of the token is stored only in:

```text
cloudflare/gca-registration-worker/.env.admin.local
```

That file is ignored by git and must not be committed or shared publicly.

To read recent email registrations:

```bash
cd cloudflare/gca-registration-worker
set -a
. ./.env.admin.local
set +a

curl -fsS 'https://gca-registration-api.gcagochina.workers.dev/gca/email-registrations?limit=20' \
  -H "authorization: Bearer $ADMIN_READ_TOKEN"
```

## Custom Domain Activation

Use this only after logging into the Cloudflare account that owns the `gcagochina.com` zone, or after adding the current Cloudflare account as a member with zone and Worker permissions.

1. Confirm the account can see the zone:

```bash
dig +short NS gcagochina.com
```

2. Copy the custom-domain example over the active Wrangler config:

```bash
cp wrangler.custom-domain.example.toml wrangler.toml
```

3. Deploy:

```bash
npx wrangler deploy
```

4. Verify:

```bash
dig +short api.gcagochina.com
curl -fsS https://api.gcagochina.com/health
```

5. After `api.gcagochina.com` is live, update `site/register.html`, `site/access-api.json`, and this document to use `https://api.gcagochina.com` as the production API base, then run the public-site checks and push.

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
