# Notes for the lesson plan

For Laura Paglione, who is writing the lesson plan, docs and slides for the COmanage Registry PE 5.2.0 workshop. They
describe what participants will have in front of them, so the material can match it. Everything here was checked on
the kit.

## Try it first

Please run the kit on your own computer, as a participant would: follow "Before the workshop" in the
[participant guide](participant-guide.md). In short, with Docker Desktop and Git installed:

```bash
git clone https://github.com/graemevarga/comanage-pe-workshop.git
cd comanage-pe-workshop
docker compose up --wait
```

Then open <https://localhost:8443/registry/> and log in as `admin` with an empty password. Anything that doesn't
work, or reads differently from what you see, is worth reporting: the participants will hit it too.

Writing and taking screenshots against the kit means the addresses, the version, the menus and the ids in your
material match what participants see.

## What participants start with

Participants run the one command above and get a fresh install, plus only what the lesson needs around it:

| | |
|---|---|
| **Address** | <https://localhost:8443/registry/>, upstream's default path. (Your current instance uses `/registry-pe/` on another host, so screenshots taken there show a different address.) Browsers warn once about the self-signed certificate. |
| **Login** | A Basic-auth prompt: any username, empty password. `admin` is the platform administrator; its display name is "Registry Admin". Any other username is whoever has that login identifier, or a new person with no COs, who can accept an invitation or sign up. Use a private window per person. |
| **Data** | Only the COmanage CO and the platform administrator. No other COs, no people, no message templates. |
| **Plugins** | Installed but **Suspended**. The lesson activates what it needs, as `admin` in the COmanage CO: **Configuration → Platform-Wide Configuration → Plugins**, gear menu on the row → **Activate** (FileConnector for the FileSource and the File Provisioner, SqlConnector for the SQL Provisioner). If you'd rather they start active, that is a one-line change in the kit. |
| **Mail** | Already goes to Mailpit: an Outgoing SMTP Server "Mailpit (workshop mail catcher)" on the COmanage CO, which every CO uses. Participants read all mail at <http://localhost:8025/>. |
| **FileSource input** | `hr.csv` and `registrar.csv`, at `/srv/filesource/hr.csv` and `/srv/filesource/registrar.csv` in the Registry: 45 fictional people each (Shayna Atkinson's v4 training population, converted to CSV v3, with a `uid` column added). |
| **File Provisioner output** | `/srv/provisioned/output.jsonl` in the Registry (the File Name to enter), which is `provisioned/output.jsonl` in the folder participants can open on their laptop. 5.2.0 requires the file to exist before the provisioner is saved; the kit creates it, empty. |
| **SQL Provisioner target** | A separate PostgreSQL database: host `target-database`, port 5432, database `target`, username `target_user`, password `password`. |

The columns of the CSV files: `SORID`, `names.given.official`, `names.family.official`, `identifiers.identifier.uid`,
and in `registrar.csv` also `identifiers.identifier.eppn`. Ruth Spence is in `hr.csv`, Lamar Martin in
`registrar.csv`. If the lesson needs other files, send them: they go into the kit's `filesource` folder and must
follow the CSV v3 rules in the [instructor guide](instructor-guide.md#lauras-csv-files).

## Commands participants may type

Only a few things need a terminal. These forms work in macOS Terminal, Windows PowerShell and Linux, run in the
`comanage-pe-workshop` folder:

| To | Command |
|---|---|
| Run a full FileSource sync (5.2.0 has no button for it) | `docker compose exec -u www-data -w /srv/comanage-registry/app registry ./bin/cake job -c <CO id> -j CoreJob.SyncJob -s external_identity_source_id=<source id>` |
| Look at the SQL Provisioner's tables | `docker compose exec target-database psql -U target_user -d target`, then `\dt` and `select * from <table>;` |
| Start over from a fresh install | `docker compose down -v`, then `docker compose up --wait` |

The sync prints the Registry's (very verbose) log; the result is in the CO under **Operations → Jobs**: "Sync
Finished (45 new, 0 updated, 0 errors, 45 total)". The ids appear in the page addresses (`co_id=3`,
`external-identity-sources/edit/1`).

## FileSource in 5.2.0

Verified on the kit; click paths in the [instructor guide](instructor-guide.md#filesource):

- A Pipeline must exist before the External Identity Source. Always choose **Person Status On Create** (for example
  Active): left blank, every synced record fails.
- The External Identity Source's Status must be **Full** (or Manual/Update). Syncing a **Disabled** source throws an
  error in 5.2.0.
- File Name is the path inside the Registry (`/srv/filesource/hr.csv`); File Format **CSV v3**.
- A full sync is command line only (above). In the UI, **Search Source → Retrieve → Sync Record to CO** syncs one
  person at a time.
- Rows removed from the file are **not** processed in 5.2.0 (the sync logs an error per missing row). Show people
  leaving by changing their role's status, not by deleting rows.
- File-sourced people have no login identifier, so they can't log in, unless the pipeline adds one (PipelineToolkit's
  Identifier Mapper flange, see the instructor guide) or an Identifier Assignment marks one as Login.

## Things to decide

1. **Plugins**: activated by participants during the lesson (as now), or already active?
2. **Anything else that should exist before the first chapter** (a CO, a pipeline...)? The kit's setup step can
   create it, so participants start exactly where the lesson begins.
3. **The CSV files**: keep these, or send yours.
4. **Prerequisites**: the participant guide asks for Docker Desktop (or Docker Engine on Linux) and Git, 8 GB of
   memory and 5 GB of disk. Docker Desktop needs a paid subscription for professional use at larger organisations
   and government; worth a line in your material.
5. **Time zones**: the Registry shows times in each browser's time zone, so dates in screenshots will differ from
   what participants see.
