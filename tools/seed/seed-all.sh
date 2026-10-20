#!/bin/bash
#
# Re-create every workshop checkpoint (instructors and maintainers).
#
#   tools/seed/seed-all.sh [FIRST_STAGE]     e.g. "tools/seed/seed-all.sh 05" redoes 05 and 06 only
#
# Starts from the Registry's real first start ("./workshop reset": empty database, upstream setup), or from the
# checkpoint before FIRST_STAGE, then for each stage drives the UI with Playwright (tools/seed/seed.py), runs the
# command-line steps and saves the checkpoint into checkpoints/. Screenshots of every step land in tools/seed/out/.
set -euo pipefail
cd "$(dirname "$0")/../.."
first="${1:-01}"
ui() { tools/seed/pw seed.py "$@"; }
stage_wanted() { [[ "$1" > "${first}" || "$1" == "${first}" ]]; }

docker compose up -d
if [[ "${first}" == "01" ]]; then
    ./workshop reset
else
    prev=$(printf '%02d' $((10#${first} - 1)))
    ./workshop restore "$(basename "$(ls checkpoints/${prev}-*.dump)" .dump)"
fi
rm -f tools/seed/out/s*.png

if stage_wanted 01; then
    ui 01
    ./workshop checkpoint 01-email "Fresh install plus Mailpit as the Outgoing SMTP Server; admin has a verified email (admin@workshop.test)"
fi
if stage_wanted 02; then
    ui 02
    ./workshop checkpoint 02-configuration "FileConnector + PipelineToolkit active; COs Discovery TNG (2), Redcurrant University (3), Guests (4), MESS (5); Discovery TNG affiliation type Principal Investigator"
fi
if stage_wanted 03; then
    ui 03
    ./workshop checkpoint 03-connections "Redcurrant University: pipeline 'Process HR API Inputs' (match on UID) and API user co_3.hr_api_user"
fi
if stage_wanted 04; then
    eis=$(ui 04 | sed -n 's/^EIS_ID=//p')
    ./workshop sync 3 "${eis}"
    ./workshop checkpoint 04-filesource-synced "Redcurrant University: FileSource 'HR File' (hr.csv) fully synced, 45 people who can log in with their uid (e.g. ruth.spence)"
fi
if stage_wanted 05; then
    ui 05
    ./workshop checkpoint 05-org-structure "COUs (Redcurrant: Alumni, Faculty/Staff, Retirees, Students; Discovery TNG: arbovirus), group Access-wiki nested from Retirees, Lamar Martin (admin), Ruth Spence (Associate Professor), Claude Larkin (PI)"
fi
if stage_wanted 06; then
    ui 06
    ./workshop checkpoint 06-enrollment "Discovery TNG: self-signup flow 'Join Discovery TNG' (email verification through Mailpit, login identifier from the username, COU arbovirus) and its message templates"
fi
./workshop list
