#!/bin/bash
#
# Re-create every workshop checkpoint (instructors and maintainers).
#
#   tools/seed/seed-all.sh [FIRST_STAGE]     e.g. "tools/seed/seed-all.sh 05" redoes 05 and 06 only
#
# Starts the image built from this checkout with the author overlay (checkpoints are written to
# image/checkpoints/), then for each stage: drive the UI with Playwright (tools/seed/seed.py), run the
# command-line steps, and save the checkpoint. Afterwards rebuild the image to bake the new dumps in.
# Screenshots of every step land in tools/seed/out/.
set -euo pipefail
cd "$(dirname "$0")/../.."
first="${1:-01}"
compose=(docker compose -f compose.yaml -f compose.build.yaml -f compose.author.yaml)
ws() { "${compose[@]}" exec -T registry workshop "$@"; }
ui() { tools/seed/pw seed.py "$@"; }
stage_wanted() { [[ "$1" > "${first}" || "$1" == "${first}" ]]; }

echo "==> Starting the workshop container (author overlay)"
"${compose[@]}" up -d
for _ in $(seq 1 90); do
    [[ "$(docker inspect -f '{{.State.Health.Status}}' "$("${compose[@]}" ps -q registry)")" == healthy ]] && break
    sleep 2
done

if [[ "${first}" == "01" ]]; then
    ws rebuild-bare
else
    prev=$(printf '%02d' $((10#${first} - 1)))
    ws restore "$(basename "$(ls image/checkpoints/${prev}-*.dump)" .dump)"
fi
rm -f tools/seed/out/s*.png

if stage_wanted 01; then
    ui 01
    ws checkpoint 01-fresh "Bare install: platform admin 'admin', Mailpit as the Outgoing SMTP Server, no plugins or COs yet"
fi
if stage_wanted 02; then
    ui 02
    ws checkpoint 02-configuration "FileConnector + PipelineToolkit active; COs Discovery TNG (2), Redcurrant University (3), Guests (4), MESS (5); Discovery TNG affiliation type Principal Investigator"
fi
if stage_wanted 03; then
    ui 03
    ws checkpoint 03-connections "Redcurrant University: pipeline 'Process HR API Inputs' (match on UID) and API user co_3.hr_api_user"
fi
if stage_wanted 04; then
    eis=$(ui 04 | sed -n 's/^EIS_ID=//p')
    ws sync 3 "${eis}"
    ws checkpoint 04-filesource-synced "Redcurrant University: FileSource 'HR File' (hr.csv) fully synced, 45 people who can log in with their uid (e.g. ruth.spence)"
fi
if stage_wanted 05; then
    ui 05
    ws checkpoint 05-org-structure "COUs (Redcurrant: Alumni, Faculty/Staff, Retirees, Students; Discovery TNG: arbovirus), group Access-wiki nested from Retirees, Lamar Martin (admin), Ruth Spence (Associate Professor), Claude Larkin (PI)"
fi
if stage_wanted 06; then
    ui 06
    ws checkpoint 06-enrollment "Discovery TNG: self-signup flow 'Join Discovery TNG' (email verification through Mailpit, login identifier from the username, COU arbovirus) and its message templates"
fi
ws list
echo "==> Done. Rebuild the image to bake these checkpoints in: make build"
