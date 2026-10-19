# syntax=docker/dockerfile:1
#
# COmanage Registry PE 5.2.0 - all-in-one workshop image
#
#   Registry 5.2.0 (Apache + mod_php, anonymous Basic auth), PostgreSQL 15, Mailpit and a queued-job
#   runner, supervised by supervisord. The database is initialised at build time, so a container is
#   ready in seconds and every participant starts from byte-identical state.
#
#   DEMO ONLY: anyone who can reach the HTTPS port can log in as the platform administrator "admin".
#   Publish the ports on 127.0.0.1 only (compose.yaml does).
#
#   Source: the upstream Internet2 COmanage Registry tag 5.2.0, verified against the tag commit.
#   Upstream's container entrypoint (comanage_utils.sh) is used unmodified; see bin/workshop-entrypoint.

ARG PHP_IMAGE=php:8.3.35-apache-bookworm@sha256:b79a53c3fb1dd4b9f350a8d99d84951512b6c21044e61bbecfee8af030b3722e

######## Stage 1: fetch the tagged source once, on the build host's own architecture ########
FROM --platform=$BUILDPLATFORM ${PHP_IMAGE} AS src
ARG REGISTRY_TAG=5.2.0
ARG REGISTRY_COMMIT=c5e9be6fddbd2b659d89741e2178edb95d5388f0
RUN set -eux; \
    curl -fsSL --retry 5 -o /tmp/registry.tar.gz \
      "https://github.internet2.edu/COmanage/registry/archive/refs/tags/${REGISTRY_TAG}.tar.gz"; \
# git-archive tarballs record the commit id in their pax header: refuse anything but the tag commit
    test "$(gzip -dc /tmp/registry.tar.gz | head -c 1536 | grep -a -o 'comment=[0-9a-f]*' | cut -d= -f2)" = "${REGISTRY_COMMIT}"; \
    mkdir /src; \
    tar -xzf /tmp/registry.tar.gz --strip-components=1 -C /src; \
    rm /tmp/registry.tar.gz

######## Stage 2: the workshop image ########
FROM ${PHP_IMAGE}

ARG TARGETARCH
ARG MAILPIT_VERSION=v1.31.6
ARG MAILPIT_SHA256_AMD64=10fa12ccc610f653d4ed4df848c1817f9935dcf4e9a6a458a19ab0fa02093f91
ARG MAILPIT_SHA256_ARM64=de07955b783236d9129da76da9a5970f1777834a18b2c07611de957be784dafe
# URL path of the application. Laura's v5.2 docs use /registry-pe/; upstream's default is /registry/.
ARG COMANAGE_REGISTRY_WEBROOT=registry-pe

# PHP extensions 5.2.0 needs on top of the official image for PostgreSQL: intl, pdo_pgsql, pcntl
# (pcntl is unused at 5.2.0 but harmless), plus opcache. The -dev packages are purged afterwards,
# keeping only the runtime libraries the new extensions link against (docker-library pattern).
RUN set -eux; \
    savedAptMark="$(apt-mark showmanual)"; \
    apt-get update; \
    apt-get install -y --no-install-recommends libicu-dev libpq-dev; \
    docker-php-ext-install -j"$(nproc)" intl pdo_pgsql pcntl; \
    docker-php-ext-enable opcache; \
    apt-mark auto '.*' > /dev/null; \
    [ -z "$savedAptMark" ] || apt-mark manual $savedAptMark > /dev/null; \
    find /usr/local/lib/php/extensions -type f -name '*.so' -exec ldd '{}' ';' \
      | awk '/=>/ { so = $(NF-1); if (index(so, "/usr/local/") == 1) { next }; gsub("^/(usr/)?", "", so); print so }' \
      | sort -u | xargs -r dpkg-query --search | cut -d: -f1 | sort -u | xargs -r apt-mark manual; \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
    rm -rf /var/lib/apt/lists/*; \
    cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini"; \
    php -r 'foreach (["intl", "pdo_pgsql", "pcntl", "mbstring", "dom", "posix", "Zend OPcache"] as $e) { if (!extension_loaded($e)) { fwrite(STDERR, "missing PHP extension $e\n"); exit(1); } }'

# PostgreSQL 15 and supervisord from Debian bookworm. create_main_cluster=false stops Debian from
# creating its own "15/main" cluster; workshop-init-db creates the workshop cluster below.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends postgresql-common; \
    echo 'create_main_cluster = false' >> /etc/postgresql-common/createcluster.conf; \
    apt-get install -y --no-install-recommends postgresql-15 postgresql-client-15 supervisor; \
    rm -rf /var/lib/apt/lists/*; \
    test ! -e /etc/postgresql/15/main

# Mailpit catches every message the Registry sends: SMTP on 127.0.0.1:1025, web UI on :8025.
RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) sha256="${MAILPIT_SHA256_AMD64}" ;; \
      arm64) sha256="${MAILPIT_SHA256_ARM64}" ;; \
      *) echo "unsupported architecture: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL --retry 5 -o /tmp/mailpit.tar.gz \
      "https://github.com/axllent/mailpit/releases/download/${MAILPIT_VERSION}/mailpit-linux-${TARGETARCH}.tar.gz"; \
    echo "${sha256}  /tmp/mailpit.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/mailpit.tar.gz -C /usr/local/bin mailpit; \
    rm /tmp/mailpit.tar.gz; \
    mailpit version --no-release-check

# Registry configuration consumed by upstream's comanage_utils.sh and by the app.
# The salt is deliberately fixed (demo only) so checkpoints restore identically in every container;
# SECURITY_SALT is set as well so web requests and CLI commands always use exactly the same value.
# Never set COMANAGE_REGISTRY_DATABASE_ENCODING (5.2.0 writes it as the connection time zone), and
# keep "'" out of the database password (it is written inside PHP single quotes).
ENV COMANAGE_REGISTRY_CONTAINER=1 \
    COMANAGE_REGISTRY_VERSION=5.2.0 \
    COMANAGE_REGISTRY_DIR=/srv/comanage-registry \
    COMANAGE_REGISTRY_WEBROOT=${COMANAGE_REGISTRY_WEBROOT} \
    COMANAGE_REGISTRY_ADMIN_GIVEN_NAME=Registry \
    COMANAGE_REGISTRY_ADMIN_FAMILY_NAME=Admin \
    COMANAGE_REGISTRY_ADMIN_USERNAME=admin \
    COMANAGE_REGISTRY_DATABASE_HOST=127.0.0.1 \
    COMANAGE_REGISTRY_DATABASE=registry \
    COMANAGE_REGISTRY_DATABASE_USER=registry_user \
    COMANAGE_REGISTRY_DATABASE_USER_PASSWORD=password \
    COMANAGE_REGISTRY_SECURITY_SALT=930c5c71809f7fae25763c352dfbadc7f18142a0 \
    SECURITY_SALT=930c5c71809f7fae25763c352dfbadc7f18142a0 \
    COMANAGE_REGISTRY_NO_EMAIL_CONFIG=1 \
    COMANAGE_REGISTRY_VIRTUAL_HOST_FQDN=localhost \
    DEBUG=false \
    PGDATA=/var/lib/postgresql/data \
    TZ=America/Chicago \
    WORKSHOP_HTTPS_PORT=8443 \
    WORKSHOP_MAILPIT_PORT=8025 \
    JOB_INTERVAL=60 \
    PATH=/usr/lib/postgresql/15/bin:$PATH

WORKDIR /srv/comanage-registry
COPY --from=src /src/app ./app/
COPY --from=src /src/LICENSE /src/NOTICE ./
COPY --from=src /src/container/registry/base/comanage_utils.sh /usr/local/lib/comanage_utils.sh
COPY --from=src --chmod=0755 /src/container/registry/base/docker-comanage-entrypoint /usr/local/bin/docker-comanage-entrypoint

# Same layout and Apache preparation as upstream's base image, plus mod_authn_anon and a localhost
# certificate that macOS/iOS accept as a click-through exception (SAN, serverAuth, <= 825 days).
RUN set -eux; \
    mkdir -p local/config local/logs local/tmp/sessions local/tmp/cache/persistent \
             local/tmp/cache/views local/tmp/cache/models local/filesource; \
    ln -s "${COMANAGE_REGISTRY_DIR}/app/webroot" "/var/www/html/${COMANAGE_REGISTRY_WEBROOT}"; \
    chown -h www-data:www-data "/var/www/html/${COMANAGE_REGISTRY_WEBROOT}"; \
    a2enmod headers ssl rewrite authn_anon; \
    a2dissite 000-default.conf; \
    a2disconf other-vhosts-access-log; \
    printf '%s\n' '[req]' 'prompt = no' 'distinguished_name = dn' 'x509_extensions = v3' \
      '[dn]' 'CN = localhost' 'O = COmanage PE workshop (demo only)' \
      '[v3]' 'subjectAltName = DNS:localhost, IP:127.0.0.1' 'extendedKeyUsage = serverAuth' \
      'keyUsage = critical, digitalSignature, keyEncipherment' 'basicConstraints = critical, CA:FALSE' \
      'subjectKeyIdentifier = hash' > /tmp/cert.cnf; \
    openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 825 -config /tmp/cert.cnf \
      -keyout /etc/apache2/privkey.pem -out /etc/apache2/cert.pem; \
    chmod 0600 /etc/apache2/privkey.pem; \
    rm /tmp/cert.cnf

# Our own vhost (anonymous login). prepare_virtual_host() never overwrites an existing 000-comanage.conf.
COPY apache/000-comanage.conf.tmpl /tmp/000-comanage.conf.tmpl
RUN set -eux; \
    sed "s#@WEBROOT@#${COMANAGE_REGISTRY_WEBROOT}#g" /tmp/000-comanage.conf.tmpl \
      > /etc/apache2/sites-available/000-comanage.conf; \
    rm /tmp/000-comanage.conf.tmpl

COPY supervisord.conf /usr/local/etc/supervisord.conf
COPY postgres/ /opt/workshop/postgres/
COPY --chmod=0755 bin/ /usr/local/bin/
COPY --chown=www-data:www-data data/filesource/ ${COMANAGE_REGISTRY_DIR}/local/filesource/
COPY data/ /opt/workshop/data/
COPY checkpoints/ /opt/workshop/checkpoints/

# Create the database cluster and the Registry database: restore checkpoint 01-fresh if it is baked in,
# otherwise run upstream's first start (bin/cake database + setup).
RUN /usr/local/bin/workshop-init-db

HEALTHCHECK --interval=15s --timeout=5s --start-period=120s --retries=20 \
  CMD curl -fsk -o /dev/null -A workshop-healthcheck "https://localhost/${COMANAGE_REGISTRY_WEBROOT}/" || exit 1

LABEL org.opencontainers.image.title="COmanage Registry PE 5.2.0 workshop" \
      org.opencontainers.image.description="All-in-one COmanage Registry PE 5.2.0 + PostgreSQL + Mailpit for hands-on workshops. Demo only: anonymous login, bind to 127.0.0.1." \
      org.opencontainers.image.source="https://github.com/graemevarga/comanage-pe-workshop" \
      org.opencontainers.image.licenses="Apache-2.0" \
      comanage_registry_version="5.2.0" \
      comanage_registry_commit="c5e9be6fddbd2b659d89741e2178edb95d5388f0"

EXPOSE 80 443 8025
# The php:apache base image sets SIGWINCH (graceful Apache stop); supervisord needs SIGTERM.
STOPSIGNAL SIGTERM
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/usr/local/etc/supervisord.conf"]
