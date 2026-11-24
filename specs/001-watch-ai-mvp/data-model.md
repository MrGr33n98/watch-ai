# Data Model — PostgreSQL, schema inicial

## `users`
- `id uuid pk`, `created_at timestamptz`, `deleted_at timestamptz NULL`; sem armazenar telefone em claro como id público.

## `authorized_senders`
- `id uuid pk`, `user_id fk`, `sender_hmac text unique`, `active boolean`, `created_at`, `revoked_at`. HMAC normalizado de número/chatID com secret do backend.

## `study_sessions`
- `id uuid pk`, `user_id fk`, `status enum`, `expected_question_count smallint default 4`, `received_count smallint`, `created_at`, `completed_at`, `expires_at`, `version int`.
- CHECK expected_question_count BETWEEN 1 AND 4. CHECK received_count BETWEEN 0 AND 4.

## `questions`
- `id uuid pk`, `session_id fk`, `ordinal smallint`, `status enum`, `statement_text text nullable`, `problem_type text nullable`, `confidence enum`, `final_answer text nullable`, `units text nullable`, `verification_status enum`, `created_at`, `updated_at`.
- UNIQUE(session_id, ordinal); CHECK ordinal BETWEEN 1 AND 4.

## `media_assets`
- `id uuid pk`, `question_id fk nullable`, `sha256 char(64)`, `mime text`, `size_bytes bigint`, `width int`, `height int`, `storage_key text`, `created_at`, `deleted_at`; armazenamento privado, sem URLs persistentes públicas.

## `solution_steps`
- `id uuid pk`, `question_id fk`, `ordinal smallint`, `kind text`, `title text`, `plain_text text`, `latex text nullable`, `render_asset_id fk nullable`, `verification_status enum`, `created_at`.
- UNIQUE(question_id, ordinal).

## `watch_devices`
- `id uuid pk`, `user_id fk`, `device_name text`, `token_hash text`, `refresh_hash text nullable`, `last_seen_at`, `revoked_at`, `created_at`.

## `inbound_messages`
- `id uuid pk`, `provider text`, `provider_message_id text`, `sender_hmac text`, `media_sha256 text nullable`, `session_id fk nullable`, `state text`, `received_at`, UNIQUE(provider, provider_message_id).

## `outbox_events`
- `id uuid pk`, `aggregate_type text`, `aggregate_id uuid`, `event_type text`, `payload jsonb`, `created_at`, `published_at`, `attempt_count int`.

## Enumerations

Session: created, collecting, queued, processing, ready, partial, needs_review, failed, cancelled, expired.
Question: uploaded, validating, interpreting, solving, ready, needs_review, failed.
Verification: verified, unverified, inconclusive, rejected.
Confidence: high, medium, low.

## Migração e integridade

Alembic migrações com constraints, UNIQUE e FK, índices `(user_id, created_at desc)`, `(session_id, ordinal)`, `(state, received_at)`, `(published_at)`; delete de mídia coordenado via job; não acoplar lifecycle de storage ao ON DELETE SQL.
