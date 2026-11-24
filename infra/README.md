# API and PostgreSQL Compose stack

`docker-compose.yml` is a local and isolated staging stack, not a production
deployment definition. It binds the API and PostgreSQL to loopback, uses a local
`.env` file, and does not provision HTTPS ingress, a secrets manager, backups, or
a scheduler. Never expose its database port to the Internet. For a staging
rollout, use a dedicated host/project, an external TLS reverse proxy and firewall
rules, non-example credentials, encrypted backups, and the release procedure in
[`docs/09_ENV_RUNBOOK.md`](../docs/09_ENV_RUNBOOK.md). A public deployment is not
configured by this repository.

## Start a disposable local stack

```sh
cp infra/.env.example infra/.env
# Replace POSTGRES_PASSWORD and the matching password in DATABASE_URL.
chmod 600 infra/.env
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml config --quiet
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml up -d --build db
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml build api
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml run --rm --no-deps api alembic upgrade head
docker compose --env-file infra/.env -p watch-ai-local -f infra/docker-compose.yml up -d api
```

The API and PostgreSQL bind to `127.0.0.1` only. The API exposes `/health`; it
reports process liveness and does not prove database or provider readiness. Set
`APP_ENV=production` for a staged service so `/dev/ingest` is not mounted. Keep
`ENABLE_WAHA_INGEST=false` until isolated WAHA credentials and sender/session
allowlists have passed QA. PostgreSQL data and private media are stored in the
`postgres_data` and `watch_ai_private_media` named volumes under the Compose
project name (`watch-ai-local` in the commands above). The host PostgreSQL port
defaults to `15432` and remains loopback-only.

Compose reads `.env` for interpolation; do not print `docker compose config` in
logs after real secrets have been added. `.env.example` contains disposable
values only. See the runbook for migration, backup, retention, incident, and
rollback procedures.
