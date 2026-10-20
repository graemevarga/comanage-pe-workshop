#!/bin/bash
#
# The workshop's one-time setup, run by the workshop-setup service (compose.yaml) once the Registry's first start
# has created its database. It only prepares what the lesson needs around the Registry; everything else is done in
# the UI during the lesson. Safe to run again: it changes nothing the second time.
set -euo pipefail

echo "workshop-setup: pointing the Registry's outgoing mail at Mailpit"
psql -v ON_ERROR_STOP=1 -q -f /setup/mail.sql

# The web server (www-data, uid 33) must be able to write the File Provisioner's output into the provisioned/ folder,
# which belongs to you on your laptop. Docker Desktop (macOS, Windows) allows that anyway; Linux needs the mode.
echo "workshop-setup: making provisioned/ writable for the Registry's web server"
chmod 0777 /provisioned 2> /dev/null || true
if ! gosu 33:33 sh -c 'touch /provisioned/.write-test && rm -f /provisioned/.write-test'; then
    echo "workshop-setup: ERROR: the Registry cannot write to the provisioned/ folder. On Linux: chmod 0777 provisioned" >&2
    exit 1
fi

echo "workshop-setup: done"
