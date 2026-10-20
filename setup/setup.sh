#!/bin/bash
#
# The workshop's one-time setup, run by the workshop-setup service (compose.yaml) once the Registry's first start
# has created its database. It only prepares what the lesson needs around the Registry; everything else is done in
# the UI during the lesson. Safe to run again: it changes nothing the second time.
set -euo pipefail

# A Registry database without an SMTP server on the COmanage CO is a fresh one (first start, or after
# "docker compose down -v"): the File Provisioner's old output then belongs to a database that is gone.
fresh=$(psql -v ON_ERROR_STOP=1 -Atqc "select count(*) = 0 from servers
    where co_id = 1 and plugin = 'CoreServer.SmtpServers' and server_id is null and deleted is not true")

echo "workshop-setup: pointing the Registry's outgoing mail at Mailpit"
psql -v ON_ERROR_STOP=1 -q -f /setup/mail.sql

# The File Provisioner appends to a file that must already exist and be writable by the web server (www-data,
# uid 33) when the provisioner is saved. It lives in provisioned/, which belongs to you on your laptop: Docker
# Desktop (macOS, Windows) lets the container write there anyway; on Linux the modes below do it.
echo "workshop-setup: preparing provisioned/output.jsonl for the File Provisioner"
chmod 0777 /provisioned 2> /dev/null || true
[ -e /provisioned/output.jsonl ] || install -m 0666 /dev/null /provisioned/output.jsonl
if [ "${fresh}" = t ] && [ -s /provisioned/output.jsonl ]; then
    echo "workshop-setup: fresh database, so emptying provisioned/output.jsonl"
    : > /provisioned/output.jsonl
fi
if ! gosu 33:33 test -w /provisioned/output.jsonl; then
    echo "workshop-setup: ERROR: the Registry cannot write provisioned/output.jsonl." \
         "On Linux: chmod 0777 provisioned && chmod 0666 provisioned/output.jsonl" >&2
    exit 1
fi

echo "workshop-setup: done"
