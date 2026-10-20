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
| **Data** | Only the COmanage CO and the platform administrator. Participants create the COs and most of the configuration themselves in the UI during the lesson: no other COs, no people, no pipelines, no message templates. |
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
| Run queued jobs, for example after Reprovision All | `docker compose exec -u www-data -w /srv/comanage-registry/app registry ./bin/cake job -r -c <CO id>` |
| Look at the SQL Provisioner's tables | `docker compose exec target-database psql -U target_user -d target`, then `\dt` and `select * from <table>;` |
| Start over from a fresh install | `docker compose down -v`, then `docker compose up --wait` |

The sync prints the Registry's (very verbose) log. To see the result, open the job in the CO under **Operations →
Jobs** (the list itself only says "Started via JobCommand"): its summary reads "Sync Finished (45 new, 0 updated,
0 errors, 45 total)". The ids appear in the page addresses (`co_id=3`,
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

## Provisioning in 5.2.0 (File and SQL Provisioners)

Verified on the kit; click paths in the instructor guide
([File](instructor-guide.md#provisioning-file-provisioner), [SQL](instructor-guide.md#provisioning-sql-provisioner)):

- The SQL Provisioner needs a **Server** first (Connections → Related Configurations → Servers, plugin
  `CoreServer.SqlServers`: Postgres, host `target-database`, database `target`, user `target_user`, password
  `password`). Saving the SQL Provisioner creates its tables (`sp_people`, `sp_names`, ...) in the target database.
- **Create provisioning targets with Provisioning Mode Disabled**, fill in the plugin's form (File Name, or Server and
  prefix), and only then switch to **Immediate**. The default mode is Queue on Error, and a target whose plugin form
  was never saved makes **every person save in that CO fail with an error page** until the target is fixed or
  deleted. Worth a warning on the slide.
- **People already in the Registry are not sent until something about them changes.** A good moment for the lesson:
  "now change Ruth's title and watch the file / the table update". To send everyone at once, Reprovision All only
  queues jobs, which need a command (`bin/cake job -r -c <CO id>`, see the instructor guide); per person, there is
  **Provision Now** on the person's Provisioning Status page (it shows no confirmation message).
- Each line in `output.jsonl` is a whole person record (about 6.7 KB, with types and groups nested); a person who
  becomes ineligible (for example their only role expires) is written as just `{"id":45}`.
- Each person from the HR file has two names in the Registry and in `sp_names`: the primary name and the copy linked
  to the HR record. Expect the question.

## Invitations in 5.2.0

Verified on the kit; click path in the [instructor guide](instructor-guide.md#enrollment-invitation):

- Petitioner Authorization has only **Any Authenticated User** (self-signup) and **CO Administrator** in 5.2.0. An
  invitation flow uses CO Administrator.
- **The platform administrator (`admin`) can't send invitations** in a CO where it isn't a Person: the browser ends
  in "too many redirects". The inviter has to be a Person in the CO who can log in and is in **CO:admins**. If the
  FileSource pipeline gives HR people login identifiers (the Identifier Mapper flange in the instructor guide), the
  quickest is to add Ruth Spence (who then logs in as `ruth.spence`) to CO:admins.
- **Collect Enrollee Email** must be ticked (it is off by default): the invitation goes to that address.
- The invitation email is the next step's **Handoff Message Template** (context Enrollment Handoff), set on the
  step's own form; the link is `(@ENTRY_URL)`.
- **Invitation Validity is in seconds**, although the label says minutes: the default 1440 expires after 24 minutes.
  Use 0 (no expiry) in the lesson.
- **Invitees must open the link in a fresh private window.** Opened in a window that is logged in (say as `admin`),
  it shows "Permission Denied" and the invitation is now tied to that login; the fix is to terminate the petition
  and invite again.
- The invitee accepts, then the login prompt appears: any new username (with an empty password) becomes their login
  identifier. Afterwards they log in as that name.
- Declining shows the same "Enrollment Complete ... has been finalized" page as accepting (with a "Invitation
  Declined" message), and nobody is notified.
- Each invitation link works once: opening it again after accepting or declining shows an error page (a 5.2.0 bug).
  Tell participants so.

## Where participants get stuck

From test runs of the procedures on the kit:

- A pipeline's **Person Status On Create** left blank: every synced person fails. An External Identity Source left
  **Disabled**: the sync throws an error.
- The full FileSource sync has no button: it is one terminal command, and the source's number comes from the page
  address (`external-identity-sources/edit/1`). Show where to find it.
- Browsers remember logins: one private window per person. "Too many redirects" means "logged in as someone who
  can't see this page": go back to the home page or open a new private window.
- A username can sign up or accept an invitation once per database.
- Creating someone by hand who is also in a file you sync later gives two people. Sync first, or keep them apart.
- The ids (CO 2-5, source 1, 2, people) only match the slides if participants create things in exactly the order
  shown; say so, or avoid ids in the text.

## Ideas for slides

- The data flow: CSV file → External Identity Source → Pipeline (matching; a flange can add a login identifier) →
  Person in the CO → Provisioners → `output.jsonl` and the target database.
- Why people from a file can't log in unless the pipeline adds a login identifier.
- What the invitation does: CO admin → email (Mailpit) → invitee accepts and picks a login → new Person.
- Mailpit as the "fake inbox" where every verification, invitation and welcome mail arrives.
- What participants see first: the browser's certificate warning, then the browser's own sign-in box after Login
  (username `admin`, password empty). A screenshot of each saves questions.

## Things to decide

1. **Plugins**: activated by participants during the lesson (as now: FileConnector, SqlConnector, and
   PipelineToolkit if the pipeline adds login identifiers), or already active?
2. **Who sends the invitations**: a CO administrator persona is needed (above). Ruth Spence in CO:admins is the
   simplest; any Person with a login identifier works.
3. **Mail setup**: the kit configures the Outgoing SMTP Server (Mailpit) for participants, so invitation and welcome
   mail works however the other chapters go. If you'd like participants to configure it themselves (Configuration →
   Servers → Add, then CO Settings; steps in the instructor guide), we'll remove it from the kit's setup step.
4. **The CSV files**: keep these, or send yours.
5. **Prerequisites**: the participant guide asks for Docker Desktop (or Docker Engine on Linux) and Git, 8 GB of
   memory and 5 GB of disk. Docker Desktop needs a paid subscription for professional use at larger organisations
   and government; worth a line in your material.
6. **Time zones**: the Registry shows times in each browser's time zone, so dates in screenshots will differ from
   what participants see.
