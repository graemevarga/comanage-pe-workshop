# Running COmanage Registry PE 5.2.0 yourself

Everything in the workshop came from the 5.2.0 release as delivered, so you can rebuild it at home without this
repository's image. These steps produce the same `registry` container the workshop ran, with upstream's own login
(basic auth) instead of the workshop's anonymous login. Check every value against the
[COmanage Registry wiki](https://spaces.at.internet2.edu/display/COmanage/Home) before using it in production.

## 1. Get the release

```bash
curl -fsSL -o registry-5.2.0.tar.gz https://github.internet2.edu/COmanage/registry/archive/refs/tags/5.2.0.tar.gz
tar -xzf registry-5.2.0.tar.gz
cd registry-5.2.0
```

Or `git clone https://github.internet2.edu/COmanage/registry.git && cd registry && git checkout 5.2.0`. On Windows, do
this inside WSL: the container scripts break if Git converts them to CRLF line endings.

## 2. Build the images

On Linux or WSL (needs bash 4 or later and GNU getopt):

```bash
./container/build.sh -s 1 --label 5.2.0 registry basic-auth
docker image ls comanage-registry
#   comanage-registry:5.2.0-basic-auth-1   (and its base, comanage-registry-base:5.2.0-1)
```

Other authentication variants: `registry shibboleth-sp-supervisor` and `registry mod_auth_openidc`. The suffix
(`-s 1`) is yours to choose; bump it when you rebuild.

On macOS, `build.sh` stops (it needs bash 4 and GNU getopt at `/usr/bin/getopt`), so run its two builds directly.
The Dockerfile is amd64-only, so Apple Silicon builds it under emulation (slow, once):

```bash
docker build --platform linux/amd64 -t comanage-registry-base:5.2.0-1 \
  --build-arg COMANAGE_REGISTRY_VERSION=5.2.0 -f container/registry/base/Dockerfile .
docker build --platform linux/amd64 -t comanage-registry:5.2.0-basic-auth-1 \
  --build-arg COMANAGE_REGISTRY_VERSION=5.2.0 --build-arg COMANAGE_REGISTRY_BASE_IMAGE_VERSION=1 \
  -f container/registry/basic-auth/Dockerfile .
```

## 3. Run it

A starting point, close to the workshop's `compose.yaml`; put secrets in files rather than in the compose file:

```yaml
services:
  registry:
    image: comanage-registry:5.2.0-basic-auth-1
    platform: linux/amd64
    depends_on:
      registry-database:
        condition: service_healthy
    environment:
      COMANAGE_REGISTRY_ADMIN_GIVEN_NAME: Registry
      COMANAGE_REGISTRY_ADMIN_FAMILY_NAME: Admin
      COMANAGE_REGISTRY_ADMIN_USERNAME: registry.admin
      COMANAGE_REGISTRY_DATABASE_HOST: registry-database
      COMANAGE_REGISTRY_DATABASE_USER_PASSWORD_FILE: /run/secrets/database_password
      COMANAGE_REGISTRY_SECURITY_SALT_FILE: /run/secrets/security_salt
      COMANAGE_REGISTRY_VIRTUAL_HOST_FQDN: registry.example.edu
      HTTPS_CERT_FILE: /run/secrets/https_cert
      HTTPS_PRIVKEY_FILE: /run/secrets/https_key
    secrets: [database_password, security_salt, https_cert, https_key]
    volumes:
      - ./basic-auth:/etc/apache2/basic-auth:ro
    ports:
      - "443:443"
      - "80:80"

  registry-database:
    image: postgres:17
    environment:
      POSTGRES_DB: registry
      POSTGRES_USER: registry_user
      POSTGRES_PASSWORD_FILE: /run/secrets/database_password
    secrets: [database_password]
    volumes:
      - registry-database:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U registry_user -d registry"]
      interval: 5s
      retries: 30

secrets:
  database_password: { file: ./secrets/database_password }
  security_salt: { file: ./secrets/security_salt }
  https_cert: { file: ./secrets/cert.pem }
  https_key: { file: ./secrets/privkey.pem }

volumes:
  registry-database: {}
```

- `./basic-auth` is an htpasswd file: `htpasswd -c basic-auth registry.admin`. The image ships one with
  `registry.admin` / `password`; replace it. The username must match `COMANAGE_REGISTRY_ADMIN_USERNAME`.
- The salt: `openssl rand -hex 32 > secrets/security_salt`. Keep it; changing it invalidates sessions.
- `docker compose up -d`, then open `https://registry.example.edu/registry/` and log in as `registry.admin`. The first
  start creates the schema and the administrator. Every start re-applies the schema (`bin/cake database`); for a
  version upgrade, follow that release's upgrade notes (5.x also has a `bin/cake upgrade` command, which the
  entrypoint does not run).
- Behind a load balancer or proxy, see the `COMANAGE_REGISTRY_REMOTE_IP_*` variables (mod_remoteip).

## 4. Configure mail

5.2 ignores the container's email variables. As the platform administrator, in the COmanage CO:
**Configuration → Servers → Add a New Server** (plugin `CoreServer.SmtpServers`: your relay's host, port, TLS,
From and Reply-To), then **Configuration → CO Settings → Outgoing SMTP Server**. Set on the COmanage CO it applies
to every CO; a CO can override it. Test with
`docker compose exec -u www-data -w /srv/comanage-registry/app registry ./bin/cake test -t mail --recipient <person_id>`
(the person needs a verified email address).

## 5. Jobs and FileSource syncs

Queued jobs (provisioning, identifier assignment, queued group nestings) need a queue runner, and a FileSource's full
sync only runs from the command line. 5.2.0 doesn't ship a working cron image, so schedule them yourself, always as
www-data, for example from the host's crontab:

```cron
*/5 * * * *  cd /srv/registry && docker compose exec -T -u www-data -w /srv/comanage-registry/app registry ./bin/cake job -r -c 2
0 2 * * *    cd /srv/registry && docker compose exec -T -u www-data -w /srv/comanage-registry/app registry ./bin/cake job -c 2 -j CoreJob.SyncJob -s external_identity_source_id=1
```

Use one `-c <co_id>` per CO: `-c all` doesn't work in 5.2.0. Mount FileSource input files into the container
(read-only is fine) and make them readable by uid 33.

## 6. Back up and restore

```bash
docker compose exec -T registry-database pg_dump -U registry_user -Fc registry > registry-$(date +%F).dump
```

Restoring is what `./workshop restore` does: drop and recreate the database, `pg_restore --no-owner`, then
`docker compose restart registry` so the Registry clears its caches.

## 7. Things that differ from the workshop

| Workshop | Yours |
|---|---|
| Anonymous login (slashRoot vhost) | basic-auth htpasswd, or the Shibboleth SP / OIDC image variants |
| Self-signed `localhost` certificate | Your certificate |
| Demo salt and database password in the compose file | Secrets |
| Mailpit | Your SMTP relay |
| Ports on 127.0.0.1:8443 | 443, reachable by your users |
| Outgoing SMTP Server inserted by `workshop-setup` | Added once in the UI (section 4) |
| No job runner | cron or your scheduler, as above |
| Checkpoints | Real backups |
