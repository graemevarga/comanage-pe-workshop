# How the workshop maps to a real deployment

The workshop runs the COmanage Registry PE **5.2.0 release as delivered**. This page lists every setting it uses, the
upstream mechanism behind it, and what you would do differently in production. For building and running your own,
see [Running it yourself](at-home.md).

## The containers

| Service | What it is | Production equivalent |
|---|---|---|
| `registry` | The image `container/build.sh -s 1 --label 5.2.0 registry basic-auth` builds from the 5.2.0 release, unmodified (this repository's workflow runs exactly that and pushes the result to GHCR). Upstream's entrypoint (`docker-comanage-entrypoint` → `comanage_utils.sh`) writes `local/config/database.php` from the environment, prepares Apache, waits for the database, runs `bin/cake database` and `bin/cake setup`, clears caches, then starts Apache. | The same image (or the shibboleth-sp-supervisor / mod_auth_openidc variant) |
| `registry-database` | Official `postgres:17`, data in the named volume `registry-database` | Your PostgreSQL service, backed up |
| `target-database` | A second `postgres:17` (database `target`, user `target_user`), named volume `target-database` | The application database a SQL Provisioner writes to |
| `mailpit` | Official Mailpit image, accepting any SMTP credentials without TLS | Your campus SMTP relay |
| `workshop-setup` | `postgres:17` running [setup/setup.sh](../setup/setup.sh) once, after the Registry's first start: it inserts the Outgoing SMTP Server for Mailpit (the rows the UI writes) and creates the File Provisioner's output file `provisioned/output.jsonl`, writable by the web server, then exits. Mailpit waits for it, so `docker compose up --wait` returns only when everything is ready | Configure your SMTP relay in the UI once (COmanage CO → Configuration → Servers, then CO Settings) |

There is no job-runner container: 5.2.0's `build.sh` lists a `crond` product whose Dockerfile is missing from the
release, and the lesson doesn't need queued jobs. In production, schedule
`bin/cake job -r -c <co_id>` (and FileSource syncs) with cron, a Kubernetes CronJob or a small loop container
running the same image.

## Registry settings (all upstream environment variables)

| Variable | Workshop value | Notes |
|---|---|---|
| `COMANAGE_REGISTRY_ADMIN_USERNAME`, `_GIVEN_NAME`, `_FAMILY_NAME` | `admin`, Registry, Admin | Used by `bin/cake setup` on the first start only. Upstream's default username is `registry.admin`; the course material uses `admin`. |
| `COMANAGE_REGISTRY_DATABASE_HOST`, `_DATABASE`, `_USER`, `_USER_PASSWORD` | `registry-database`, `registry`, `registry_user`, `password` | Upstream's defaults, spelled out. `database.php` is written only if it doesn't exist. The password is written inside PHP single quotes: no `'`. Use the `_FILE` variants for secrets. |
| `COMANAGE_REGISTRY_SECURITY_SALT` | a fixed demo value | Without it, `setup` writes a random salt into the container, which changes whenever the container is recreated. Use `COMANAGE_REGISTRY_SECURITY_SALT_FILE` with a secret. |
| `COMANAGE_REGISTRY_VIRTUAL_HOST_FQDN` | `localhost` | Sets Apache's `ServerName`. Always set it: otherwise it is parsed from the certificate, which breaks with some SANs. |
| `HTTPS_CERT_FILE`, `HTTPS_PRIVKEY_FILE` | `registry/tls/*.pem`, mounted | Upstream copies them over the image's snakeoil certificate. The workshop's is self-signed for `localhost` and `127.0.0.1` and kept within macOS's limits (825 days, serverAuth), so browsers let you click through. Use your real certificate. |
| `COMANAGE_REGISTRY_VIRTUAL_HOST_PORT` | the published HTTPS port (8443) | Read by the workshop's vhost for its HTTP→HTTPS redirect. |
| (not set) `COMANAGE_REGISTRY_WEBROOT` | upstream default `registry` | The app is at `/registry/`. Changing it means rebuilding the image with `--build-arg COMANAGE_REGISTRY_WEBROOT=...` (the symlink is created at build time). |

Never set `COMANAGE_REGISTRY_DATABASE_ENCODING` in 5.2.0: `comanage_utils.sh` also writes it as the connection's time
zone. The `COMANAGE_REGISTRY_EMAIL_*` variables are ignored by 5.2: outgoing mail is configured in the UI
(COmanage CO → Configuration → Servers, then CO Settings → Outgoing SMTP Server).

## The one customisation: anonymous login

Upstream's basic-auth image protects `/registry/auth/login/` with `AuthBasicProvider file` and an htpasswd file
containing `registry.admin`. Benn Oshrin's workshop design uses Apache's `AuthBasicProvider anon` instead: any
username, empty password, so participants can be anyone. That can't be set with an environment variable, so the
workshop uses upstream's **slashRoot** mechanism: everything under `registry/slashRoot/` is mounted at
`/opt/registry/slashRoot` and copied over the image's filesystem at every start (`comanage_utils::process_slash_root`),
before the entrypoint would generate a vhost:

- `etc/apache2/sites-available/000-comanage.conf`: the vhost upstream generates for the basic-auth image, with
  `AuthBasicProvider anon` (`Anonymous *`, `Anonymous_NoUserID Off`, `Anonymous_MustGiveEmail Off`,
  `Anonymous_LogEmail Off`), `UseCanonicalName Off` and no HSTS (so it works on remapped localhost ports), and an
  HTTP→HTTPS redirect to the published port instead of upstream's hardcoded `:443`.
- `etc/apache2/mods-enabled/authn_anon.load`: enables `mod_authn_anon`, which Debian's Apache ships but the image
  doesn't enable.

At home, delete those two files (or the volume line) and you have upstream's basic-auth behaviour; mount your own
htpasswd at `/etc/apache2/basic-auth`. For a shared machine that still wants personas, `AuthBasicProvider file anon`
makes `admin` require its htpasswd password while every other username stays anonymous.

## Data, files and checkpoints

- Participants start from upstream's first start plus the `workshop-setup` step: no COs, no people, no active
  plugins. Everything else is built in the UI during the lesson.
- The FileSource input files are mounted read-only at `/srv/filesource` (from `filesource/`). Any path the web server
  user (www-data, uid 33) can read works; FileSource re-reads the file on every sync.
- The File Provisioner appends JSON lines to `/srv/provisioned/output.jsonl`, a bind mount of `provisioned/`, so
  participants can open the output on their laptop. 5.2.0 only accepts a file that already exists and is writable by
  www-data, so the setup step creates it (mode 0666, folder 0777 for Linux hosts; Docker Desktop doesn't care).
- Checkpoints are plain `pg_dump -Fc` files in `checkpoints/` (not committed), made and restored by the database
  container's own `pg_dump`/`pg_restore` (`./workshop checkpoint` / `restore`). A restore recreates the `registry`
  database and restarts the `registry` container, whose entrypoint clears CakePHP's caches. `tools/seed/seed-all.sh`
  walks through the lesson's procedures with Playwright from a fresh install and saves one after each chapter.
- Run `bin/cake` as **www-data** (`docker compose exec -u www-data ...`): the image's entrypoint only fixes the
  ownership of `app/tmp`, but v5 keeps its cache in `local/tmp`, so cache files created by root break the web server.

## 5.2.0 container quirks you will see (and what they mean)

- **amd64 only.** The base Dockerfile hardcodes the x86-64 LDAP library path and downloads the x86-64 Oracle Instant
  Client, so the image cannot be built for arm64. Apple Silicon Macs run it under Docker Desktop's emulation (compose
  sets `platform: linux/amd64`); the database and Mailpit run natively.
- **Every start logs a PostgreSQL error** `cannot drop index format_assigner_sequences_i1`: the entrypoint's
  `bin/cake database` re-run is not idempotent for the CoreAssigner plugin on PostgreSQL. It changes nothing.
- **`Could not find .../plugins/TermsAgreer/tests/`** and CakePHP deprecation notices appear in the log constantly.
  Harmless.
- **Startup output is hidden** unless `COMANAGE_DEBUG=1` (which also forces `DEBUG=true`), so a failed first start
  shows up only as an unhealthy container.
- **`build.sh` ignores `--image_registry`/`--repository`** and needs bash 4 and GNU getopt (not on stock macOS).
- The PHP in the image is 8.3.3, as pinned by the release.

## Security

Anonymous login means anyone who can reach the port is the administrator, so every port is published on 127.0.0.1
only, the database isn't published at all, and all data is fictional. The certificate's private key, the salt and the
database password in this repository are public demo values.
