# Design notes

For maintainers of the workshop image: why it is built the way it is, and how to change it.

## Goals

- One self-contained environment per laptop for a hands-on COmanage Registry PE workshop: Registry, database,
  mail catcher, job runner, sample data and catch-up checkpoints, with nothing else to install.
- Upstream Internet2 COmanage Registry **5.2.0** exactly as tagged (commit `c5e9be6fddbd2b659d89741e2178edb95d5388f0`),
  with upstream's container entrypoint reused unmodified.
- Benn Oshrin's specification: v5 Registry, PostgreSQL, Apache `AuthBasicProvider anon`, no Shibboleth, no LDAP,
  FileSource fed by prepared files.
- Runs natively on Apple Silicon Macs, Windows (Docker Desktop + WSL 2) and Intel/AMD Linux.

## One image, supervisord as PID 1

Everything runs in one container so a participant needs one `docker compose up -d` (or one `docker run`) and the
state lives in one place. supervisord (the pattern upstream uses for its Shibboleth SP image) runs:

| Program | What it is |
|---|---|
| `postgres` | PostgreSQL 15 from Debian bookworm, listening on 127.0.0.1 inside the container only |
| `mailpit` | Mailpit: SMTP on 127.0.0.1:1025 inside the container, web UI on port 8025 |
| `apache2` | `workshop-entrypoint apache2-foreground`: upstream's entrypoint, then Apache with mod_php |
| `jobs` | `workshop-jobs`: every `JOB_INTERVAL` seconds (60), `bin/cake job -r -c <id> -m 100` for each active CO, as www-data |

`docker compose stop`/`start` keeps all state. `docker compose down` discards the container, so the next `up` starts
from the image's state again; that is the reset participants want. A commented named volume in `compose.yaml` keeps
the database across `down` for anyone who wants that.

## Build-time database initialisation

`workshop-init-db` runs once during `docker build`. It creates the PostgreSQL cluster and the `registry` database,
then either restores the baked checkpoint `01-fresh` or (when there is none yet) runs upstream's first start
(`bin/cake database` and `bin/cake setup --admin-username admin`). It finishes by asserting that setup has run, that
`admin` is an active login identifier and that the Apache configuration parses.

Consequences:

- A new container is ready in about ten seconds, and every participant starts from byte-identical state.
- The shipped state *is* checkpoint `01-fresh`, so `workshop reset` and `docker compose down && up` agree.
- The security salt is fixed in the image (`COMANAGE_REGISTRY_SECURITY_SALT` and `SECURITY_SALT`), so checkpoints
  restore identically in any container built from the same Dockerfile. It is a demo salt; never reuse it.
  (5.2.0 only uses the salt for CSRF tokens and OrcidSource tokens.)

## Upstream entrypoint, three workshop fixes

`image/bin/workshop-entrypoint` sources upstream's `comanage_utils.sh` (copied from the tag, unmodified) and changes
three things before calling `comanage_utils::exec_apache_http_server`:

1. `OUTPUT=/dev/stdout`, so startup output reaches `docker compose logs`. Upstream discards it unless
   `COMANAGE_DEBUG` is set, which would also force `DEBUG=true`.
2. `tmp_ownership()` chowns `local/tmp` and `local/logs`. Upstream chowns `app/tmp`, but v5 keeps TMP, CACHE and LOGS
   under `local/` (`app/config/paths.php`), so the cache files the root-run start-up commands create would otherwise
   stay root-owned and break www-data.
3. At runtime it sets `COMANAGE_REGISTRY_SKIP_SETUP=1`. The schema and the COmanage CO already exist (built in, or
   restored by `workshop restore`), and in 5.2.0 the schema re-run is not idempotent: for the CoreAssigner plugin it
   tries `DROP INDEX format_assigner_sequences_i1`, which backs a constraint, and logs a PostgreSQL error on every
   start. Set `WORKSHOP_SCHEMA_SYNC=1` to run `database`/`setup` anyway (for example with a database volume from an
   older image).

Settings upstream's scripts consume are image `ENV`s: database host `127.0.0.1`, user `registry_user`, password
`password` (it is written inside PHP single quotes, so never use `'`), `COMANAGE_REGISTRY_NO_EMAIL_CONFIG=1` (5.2.0
never loads `email.php`; mail is configured in the UI), `COMANAGE_REGISTRY_VIRTUAL_HOST_FQDN=localhost` (otherwise
it is parsed from the certificate). Never set `COMANAGE_REGISTRY_DATABASE_ENCODING`: 5.2.0's `comanage_utils.sh`
writes it as the connection *time zone*.

## Anonymous login

`image/apache/000-comanage.conf.tmpl` replaces the vhost upstream would generate (upstream's basic-auth vhost hardcodes
`AuthBasicProvider file`; `prepare_virtual_host` never overwrites an existing `000-comanage.conf`). Only
`<webroot>/auth/login/` (where `login.php` copies `REMOTE_USER` into the session) is protected:

    AuthType Basic
    AuthBasicProvider anon
    Anonymous *
    Anonymous_NoUserID Off
    Anonymous_MustGiveEmail Off
    Anonymous_VerifyEmail Off
    Anonymous_LogEmail Off
    Require valid-user

Any username is accepted, the password may be blank, and `Anonymous_LogEmail Off` keeps whatever people type as a
password out of the logs. `admin` is the platform administrator because `bin/cake setup` gave that Person the login
identifier `admin`. Other names log in as whoever has that login identifier, or as an "authenticated user" with no
COs, which is what self-signup enrollment flows need.

Other differences from upstream's generated vhost: `UseCanonicalName Off` and no HSTS, so the app works behind any
localhost port mapping; plain HTTP redirects to `https://<host>:${WORKSHOP_HTTPS_PORT}/` rather than upstream's
hardcoded `:443`; health-check requests are not access-logged.

**Shared machines:** for a shared or hosted VM, change the provider to `AuthBasicProvider file anon` with an htpasswd
file that lists only `admin`. mod_auth_basic does not fall through to the next provider on a wrong password, so
`admin` then needs its password while every other username stays anonymous. Keep the ports on 127.0.0.1 (or behind a
VPN) regardless.

## TLS

The image generates a self-signed certificate for `localhost` and `127.0.0.1` at build time (RSA 2048, SHA-256,
`serverAuth`, 825 days, which macOS and iOS accept as a click-through exception). Every container from one image shares
the key, which is acceptable for localhost only. Bring your own with `HTTPS_CERT_FILE`/`HTTPS_PRIVKEY_FILE`
(upstream's mechanism).

## PHP 8.3, not 8.4

Base image `php:8.3.35-apache-bookworm` (pinned by digest). 5.2.0 runs on PHP 8.4, but emits `E_DEPRECATED` notices on
the workshop's paths (FileSource `fgetcsv()`, SyncJob, every page through StandardController) until the post-tag fix
a4236939. Extensions added: `intl`, `pdo_pgsql`, `pcntl` (unused at 5.2.0, harmless) and opcache. The committed
`vendor/` is used as shipped; don't prune it (Composer's autoload files would fatal).

## Logs

Upstream's container mode (`COMANAGE_REGISTRY_CONTAINER=1`) sends CakePHP's debug and error logs to stdout and
stderr, so web requests log verbosely to `docker compose logs`. The `workshop` CLI and the job runner unset that
variable, so their CakePHP logs go to `local/logs/cli-*.log` (`workshop logs`) and command output stays readable.
Two upstream messages appear on most requests and are harmless: `Could not find .../plugins/TermsAgreer/tests/`.

## PostgreSQL

Debian's `postgresql-15` (with `create_main_cluster = false`, so Debian doesn't create its own cluster). JIT is off
(nothing here benefits, and it avoids loading LLVM). `local` connections are `trust`; TCP from 127.0.0.1 uses
scram-sha-256. The `PATH` puts `/usr/lib/postgresql/15/bin` first, bypassing Debian's `pg_wrapper`.

## Checkpoints

`workshop checkpoint NAME [description]` writes `pg_dump -Fc` to `/opt/workshop/checkpoints/NAME.dump`.
`workshop restore NAME` stops Apache and the job runner, drops and recreates the database, restores with
`--no-owner --no-privileges --role=registry_user`, deletes PHP sessions (they describe the old database) and starts
Apache again (its entrypoint clears CakePHP's caches). A checkpoint only depends on the image's schema and salt, so it
restores on any container built from this Dockerfile. Changing the Registry version means re-creating them.

The checkpoints are produced by `tools/seed/` (Playwright driving the real UI, plus the `workshop` CLI for the steps
that only exist on the command line), so they can be regenerated when the course material changes.

## Changing the webroot or the Registry version

- Webroot: build argument `COMANAGE_REGISTRY_WEBROOT` (default `registry-pe`, which the v5.2 course material uses;
  upstream's default is `registry`). It sets the symlink, the vhost, the health check and the job runner's probe.
  Checkpoints don't depend on it.
- Registry version: change `REGISTRY_TAG` and `REGISTRY_COMMIT` in `image/Dockerfile` (the build refuses a tarball
  whose embedded commit differs), check `comanage_utils.sh` for changes, rebuild without checkpoints
  (`git rm image/checkpoints/*.dump`), regenerate them with `tools/seed/`, rebuild.

## Multi-architecture publishing

`.github/workflows/publish.yml` builds natively on GitHub's `ubuntu-24.04` (amd64) and `ubuntu-24.04-arm` (arm64)
runners, pushes each by digest, merges them into one tag with `docker buildx imagetools create`, then pulls the
published tag on both architectures and smoke-tests it (health, anonymous login, Mailpit, restoring a checkpoint).
Push a tag `v5.2.0-N` to publish `5.2.0-N`, `5.2.0` and `latest`. The first push creates a private GHCR package; make
it public once (package settings, Change visibility) so participants can pull anonymously.
