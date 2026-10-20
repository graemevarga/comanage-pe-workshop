#!/bin/bash
#
# Walk through the workshop procedures on a fresh kit and save a checkpoint after each stage (instructors).
#
#   tools/seed/seed-all.sh [FIRST_STAGE]     e.g. "tools/seed/seed-all.sh 05" redoes 05 to 07 only
#
# Starts from what participants get ("./workshop reset": empty database, upstream setup, then the workshop-setup
# step), or from the checkpoint saved before FIRST_STAGE, then for each stage drives the UI with Playwright
# (tools/seed/seed.py), runs the command-line steps and saves a checkpoint into checkpoints/ (not committed).
# Screenshots of every step land in tools/seed/out/. A failing stage stops the run: that procedure needs a look.
set -euo pipefail
cd "$(dirname "$0")/../.."
export MSYS_NO_PATHCONV=1   # Git Bash; on Windows, run the seeder from WSL instead
first="${1:-01}"
ui() { tools/seed/pw seed.py "$@"; }
stage_wanted() { [[ "$1" > "${first}" || "$1" == "${first}" ]]; }

if [[ "${first}" == "01" ]]; then
    ./workshop reset
else
    prev=$(printf '%02d' $((10#${first} - 1)))
    if [[ "${first}" == "07" ]]; then prev=04; fi   # stage 07 builds on the FileSource state
    prev_dump=$(ls checkpoints/${prev}-*.dump 2> /dev/null | head -n 1 || true)
    if [[ -z "${prev_dump}" ]]; then
        echo "seed-all.sh: stage ${first} starts from checkpoint ${prev}, which isn't saved yet." \
             "Run tools/seed/seed-all.sh (from 01) first." >&2
        exit 1
    fi
    docker compose up --wait
    ./workshop restore "$(basename "${prev_dump}" .dump)"
fi
rm -f tools/seed/out/s*.png

if stage_wanted 01; then
    ui 01
    ./workshop checkpoint 01-email "Fresh install (mail goes to Mailpit); admin has a verified email (admin@workshop.test)"
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
if stage_wanted 07; then
    # Provisioning and invitations, built on the FileSource state of 04; topics.py checks every step as it goes
    # (it runs on the host and needs python3).
    ./workshop restore 04-filesource-synced
    "${PYTHON:-python3}" tools/seed/topics.py all
    ./workshop checkpoint 07-provisioning-invitation "Redcurrant University (from 04): SqlConnector active; provisioning targets File Export (provisioned/output.jsonl) and SQL Export (target database), Immediate; Ruth Spence in CO:admins; invitation flow 'Invite a Member' and its templates; Casey Invitee enrolled by invitation (plus the test petitions of the trap checks). Restoring it doesn't restore output.jsonl or the target database."
fi
./workshop list
