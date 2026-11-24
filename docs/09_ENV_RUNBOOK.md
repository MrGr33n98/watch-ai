# Environment and operations runbook

## Scope and deployment boundary

The repository currently provides a loopback-only Docker Compose stack for local
development and isolated staging. It does not provision a production host, TLS
ingress, secret manager, object storage, scheduled jobs, alerting, or a backup
service. Do not expose PostgreSQL or the API directly to the public Internet.
For an isolated staging rollout, use a dedicated host and Compose project, a
separately managed HTTPS reverse proxy and firewall, and credentials that are
not shared with production or another project. The Wear app must connect only
through HTTPS. No provider key belongs in the APK.

Use the same Compose project name and `infra/.env` for every operation below;
the examples use `watch-ai-staging`. Restrict the env file to the service
operator (`chmod 600 infra/.env`), keep it out of version control, and prefer
the host's secrets manager for a real deployment. Compose interpolation and
`docker compose config` can reveal values: do not paste rendered config or
environment dumps into logs or tickets.

## Configuration and secret handling

The real variable names are declared in `infra/docker-compose.yml` and
`infra/.env.example`:

| Setting | Handling |
| --- | --- |
| `DATABASE_URL`, `POSTGRES_PASSWORD` | Unique random database credential; use TLS/private networking for a remote database. Never reuse the example value. |
| `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | Server-side only. Pin the approved vision model and set an approved positive `MONTHLY_MODEL_BUDGET_USD` before enabling interpretation. The budget is a preflight cap; simultaneous in-flight requests can exceed it. |
| `WAHA_API_KEY`, `WAHA_WEBHOOK_HMAC_SECRET`, `WAHA_SENDER_HASH_SECRET` | Server-side only. Generate independent random secrets of at least 32 bytes for the two HMAC/hash secrets. Rotate and revoke through the secret manager. |
| `WAHA_ALLOWED_SESSIONS`, `WAHA_ALLOWED_SENDERS`, `WAHA_SENDER_USER_IDS` | Explicit allowlists. Map every sender to an existing owner UUID (`sender=UUID`). Keep WAHA disabled until the isolated session, allowlists, and webhook authentication have passed QA. |
| `WATCH_AI_MEDIA_DIR` | Private app volume only; do not serve this directory from the web server. |
| `MEDIA_RETENTION_HOURS`, `SESSION_RETENTION_DAYS` | Set only to the approved privacy policy. Current defaults are 24 hours and 30 days. |
| Watch pairing token | Issued by the API and stored server-side as a hash. The current `DELETE /v1/devices/me` endpoint revokes only the calling watch. A lost watch cannot currently be revoked remotely; add an owner/admin revocation flow before production. There is no signing-key environment variable. |

Keep `ENABLE_WAHA_INGEST=false` and provider credentials unset for mock-only
testing. For an approved isolated WAHA environment, configure its webhook to
`https://<staging-host>/waha/webhook`, enable the integration, and verify an
authorized sender, a denied sender, and a duplicate delivery. Do not use a
production WAHA session for QA.

## Isolated staging release

1. Confirm the target host, database, media volume, ingress, DNS, TLS, firewall,
   secret injection, off-host encrypted backup destination, and restore owner are
   dedicated to this staging project. The Compose API and database ports bind to
   loopback; terminate HTTPS at a separately managed reverse proxy on the same
   host or a private network.
2. Review the exact release source and lockfiles. Build the API image from
   `apps/api/Dockerfile`; record its immutable image digest in the release log.
   The repository has no registry publishing or deployment workflow.
3. Put the approved values in the host's protected environment injection. For
   local disposable use, copy `infra/.env.example` to `infra/.env`, replace the
   example password in both locations, set `APP_ENV=production`, and use
   `chmod 600 infra/.env`. Do not save real credentials in this repository.
   If this is a new release, build the image once and record the resulting image
   ID before migration:

   ```sh
   docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml build api
   docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml images api
   ```
4. Validate Compose without printing its rendered configuration, then start
   PostgreSQL and wait for its health check:

   ```sh
   docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml config --quiet
   docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml up -d db
   docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml ps
   ```

5. Take and verify a database and media backup (procedure below). Check the
   database's current Alembic revision, then apply only forward migrations from
   the API image. The image includes the migration scripts and Alembic config;
   the API does not migrate automatically at startup.

   ```sh
   docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml run --rm --no-deps api alembic current
   docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml run --rm --no-deps api alembic heads
   docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml run --rm --no-deps api alembic upgrade head
   ```

6. Start the new API image and check process liveness and the staged HTTPS route:

   ```sh
   docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml up -d api
   docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml ps
   STAGING_HOST=watch-ai.example.test
   curl --fail --silent --show-error "https://$STAGING_HOST/health"
   ```

   `/health` is a liveness response; it does not prove database, WAHA, or model
   readiness. Confirm `/dev/ingest` returns 404 with `APP_ENV=production`, then
   use the fake-provider integration suite before enabling real providers.
   Enable WAHA and OpenRouter only after their isolated credentials, allowlists,
   budget cap, and authorized QA have been approved. Do not run provider calls
   as part of CI.

## Expand/contract database changes

The running API does not execute Alembic on boot. Apply schema changes as a
separate release step after a verified backup. Current Compose is a single API
service, so use a maintenance window and stop webhook ingress during any
non-backward-compatible step; it does not implement rolling deployment.

For each schema change, keep the migration compatible with both the currently
deployed and next API version:

1. **Expand:** add nullable columns, tables, or indexes without removing or
   renaming data used by the old API. Apply this migration first.
2. **Transition:** deploy code that can read the old and new representation;
   dual-write where needed, then backfill in bounded, observable batches.
3. **Verify:** compare row counts and application behavior; keep the prior
   representation until the new version has run successfully and the rollback
   window has expired.
4. **Contract:** remove the old column/table only in a later release after no
   deployed code reads or writes it and a fresh backup has been checked.

Do not assume `alembic downgrade` is a safe rollback. Existing downgrade
functions drop tables or columns and can destroy user data. Rollback should
normally redeploy the previous API image against the expanded compatible schema.
If data has already been removed or corrupted, stop writes and restore the
database and media set together into an isolated recovery target before
redirecting traffic. Do not restore a backup over the only current copy.

## Backup and restore

Back up PostgreSQL and the private-media volume together before migrations,
retention changes, or release rollback. Pause WAHA delivery and put ingress in
maintenance while taking the pair; check the deployed WAHA version's delivery
and replay behavior before resuming it. Encrypt backup files, copy them off the
host, restrict access, record checksums, and perform periodic restore drills in
a disposable isolated project. A checksum proves file integrity only; it does
not encrypt the backup. These commands require the same `.env` and project name
as the service. Set `BACKUP_DIR` to a protected mounted backup destination.

```sh
BACKUP_DIR=/secure/off-host/watch-ai
mkdir -m 700 -p "$BACKUP_DIR"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml stop api
docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$BACKUP_DIR/postgres-$STAMP.dump"
docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml run --rm --no-deps -T --entrypoint python api -c 'import sys,tarfile; archive=tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz"); archive.add("/app/private-media", arcname="."); archive.close()' > "$BACKUP_DIR/media-$STAMP.tar.gz"
docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml start api
sha256sum "$BACKUP_DIR/postgres-$STAMP.dump" "$BACKUP_DIR/media-$STAMP.tar.gz" > "$BACKUP_DIR/SHA256SUMS-$STAMP"
```

Before restoring, stop API/WAHA ingress and select a separate empty recovery
project and volumes. Verify the chosen dump against its recorded checksum first.
Restore PostgreSQL only into that recovery target; `pg_restore --clean` replaces
objects in the target database:

```sh
STAMP=REPLACE_WITH_BACKUP_UTC_TIMESTAMP
sha256sum --check "$BACKUP_DIR/SHA256SUMS-$STAMP"
docker compose --env-file infra/.env -p watch-ai-recovery -f infra/docker-compose.yml up -d db
docker compose --env-file infra/.env -p watch-ai-recovery -f infra/docker-compose.yml exec -T db sh -c 'pg_restore --clean --if-exists --no-owner --exit-on-error -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$BACKUP_DIR/postgres-$STAMP.dump"
```

Restore the matching media archive into the recovery project's named media
volume using the same API image (Python's `data` extraction filter rejects
archive paths outside the target directory):

```sh
docker compose --env-file infra/.env -p watch-ai-recovery -f infra/docker-compose.yml run --rm --no-deps -T -v "$BACKUP_DIR/media-$STAMP.tar.gz:/tmp/watch-ai-media.tar.gz:ro" --entrypoint python api -c 'import tarfile; archive=tarfile.open("/tmp/watch-ai-media.tar.gz", "r:gz"); archive.extractall("/app/private-media", filter="data"); archive.close()'
```

Validate Alembic revision, session/question counts, media file availability,
authorization, and `/health` in the recovery project before any traffic switch.
Recovery commands are instructions only; no backup or restore was performed
during implementation.

## Retention

`apps/api/app/maintenance/purge_retention.py` deletes expired media and sessions
using `MEDIA_RETENTION_HOURS` and `SESSION_RETENTION_DAYS`. It is not scheduled
by Compose and has no dry-run mode. Approve the retention policy, verify backup
and restore coverage, then schedule this one-shot command through an external
operator-controlled scheduler with the same protected environment:

```sh
docker compose --env-file infra/.env -p watch-ai-staging -f infra/docker-compose.yml run --rm --no-deps api python -m app.maintenance.purge_retention
```

Review the emitted deletion counts and application audit/retention records.
Never enable an unreviewed cron job or test destructive retention against
production data.

## Incident response and rollback

- **Lost or exposed watch:** if the watch still has its credential, use its
  `DELETE /v1/devices/me` action. Remote owner/admin revocation is not
  implemented, so a lost watch is a production blocker until that workflow is
  added. Do not improvise an unaudited SQL update. Review redacted request logs.
- **Leaked API/WAHA secret:** disable the corresponding integration, rotate the
  secret in its source and API environment, redeploy, and verify the old value
  is rejected. Never place the replacement in an APK or commit.
- **OpenRouter errors or spend:** disable interpretation by removing provider
  availability/credential, preserve incoming work for review, check the durable
  monthly usage ledger and configured cap, then re-enable only after the budget
  owner approves. The cap is not a transactional reservation for concurrent
  requests.
- **WAHA outage or malformed event:** keep ingestion disabled or isolated,
  inspect sanitized event state and bounded retry/dead-letter records, and replay
  only through the idempotent path after correcting the fault.
- **Database or migration failure:** stop ingress and API writes, preserve logs
  and current volumes, restore the last known good backup into a separate
  recovery project, validate it, and switch the staging ingress only after
  review. Do not blindly downgrade destructive migrations.
- **Watch offline:** the app can show cached session data; treat it as stale
  until synchronization resumes. Do not repeatedly poll or assume a cached
  answer reflects a later server update.

Record incident time, release/image digest, affected session IDs (never image
content or tokens), migration revision, actions, and recovery verification.
Rotate any credential that may have entered a log or artifact. No production
incident, deployment, credential rotation, or restore is claimed by this
runbook.
