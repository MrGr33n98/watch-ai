# API, Worker, and PostgreSQL Compose stack

`docker-compose.yml` is a local and isolated staging stack, not a production
deployment definition. It binds the API and PostgreSQL to loopback, uses a local
`.env` file, and includes an optional `tls` Caddy reverse-proxy profile for
HTTPS testing with Galaxy Watch4 and mobile browsers. Never expose its database
port to the Internet.

## Start a local stack with fake vision (no external credentials)

```sh
cp infra/.env.example infra/.env
# Replace POSTGRES_PASSWORD, DATABASE_URL password, and set a >=32-byte ADMIN_API_KEY if enabling /phone and /v1/admin/*.
chmod 600 infra/.env
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml config --quiet
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml up -d --build db
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml run --rm --no-deps api alembic upgrade head
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml up -d --build api worker
```

To enable the optional Caddy TLS reverse proxy (when `WATCH_AI_DOMAIN` points to your host):

```sh
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml --profile tls up -d caddy
```

## Operator provisioning and lost-watch revocation

```sh
# 1. Create a user UUID
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml exec api python -m app.maintenance.admin bootstrap-user
# 2. Issue an 8-character Watch4 pairing code
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml exec api python -m app.maintenance.admin create-pairing-code --user-id <USER_UUID>
# 3. List or remotely revoke a lost watch
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml exec api python -m app.maintenance.admin list-devices --user-id <USER_UUID>
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml exec api python -m app.maintenance.admin revoke-device --user-id <USER_UUID> --device-id <DEVICE_UUID>
```

When `ADMIN_API_KEY` (>= 32 bytes) is set, the mobile-friendly console at `/phone`
and the authenticated `/v1/admin/*` API also allow creating users, generating
Watch4 pairing codes, uploading 1–4 JPG files directly from the phone browser,
and remotely revoking lost watches.
