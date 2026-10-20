# Instructor guide

For whoever runs the demo: what each chapter shows, the exact click paths in Registry 5.2.0, the commands, and the
traps. Participants' instructions are in [participant-guide.md](participant-guide.md); why the kit is built this way
is in [design-notes.md](design-notes.md).

Conventions: **Configuration → API Users** means the left navigation's *Configuration* panel, then that link.
`workshop ...` is run as `docker compose exec registry workshop ...` from the repository directory.

## Before the workshop

- [ ] `docker compose pull && docker compose up -d` on the demo laptop; log in as `admin`; open Mailpit.
- [ ] Ask participants to pull the image at home (participant guide, "Before the workshop"). For the room, bring USB
      copies for people who couldn't: `docker pull --platform linux/arm64 ghcr.io/graemevarga/comanage-pe-workshop:5.2.0-1`
      then `docker save ghcr.io/graemevarga/comanage-pe-workshop:5.2.0-1 -o comanage-pe-workshop-arm64.tar` (repeat
      with `linux/amd64`). Participants run `docker load -i <file>`.
- [ ] Presenting: zoom the browser to 125-150%, use a private window per persona, keep Mailpit in a second tab.
- [ ] Optional: `DEBUG=true` in `.env` gives friendlier error pages (and the DebugKit toolbar) on your own laptop.

## How the kit fits together

| Where | What |
|---|---|
| `https://localhost:8443/registry-pe/` | The Registry. Login: any username, blank password; `admin` is the platform administrator |
| `http://localhost:8025/` | Mailpit: every message the Registry sends |
| `workshop restore NN-name` | Jump to a checkpoint (one per chapter, below); `workshop list` shows them |
| `workshop sync <co> <eis>` | Full FileSource sync (command line only in 5.2.0) |
| `image/data/filesource/` | The CSV files, also at `/srv/comanage-registry/local/filesource/` in the container |
| `tools/seed/` | The scripts that build the checkpoints by driving the UI; screenshots of every step land in `tools/seed/out/` |

Ids in a fresh kit: COs COmanage **1**, Discovery TNG **2**, Redcurrant University **3**, Guests **4**, MESS **5**.
External Identity Source "HR File" is **1**. After checkpoint 04 the HR people are Person ids 2-46 (in SORID order),
Lamar Martin 47, Claude Larkin 48.

## Chapter 1: First login and mail (state: `01-fresh`)

1. Open the Registry, accept the certificate warning, click **Login**, type `admin`, leave the password empty.
   The platform admin lands on the COmanage CO dashboard ("This is the COmanage CO, which is used for platform wide
   configurations.").
2. Mail is already wired up, because the container's email settings are ignored in 5.2:
   **Configuration → Servers** shows "Mailpit (workshop mail catcher)" (plugin `CoreServer.SmtpServers`, host
   `127.0.0.1`, port `1025`, no TLS, From `registry@workshop.test`), and **Configuration → CO Settings** →
   *Outgoing SMTP Server* points at it. Set on the COmanage CO, it applies to every CO.
3. Optional mail test: give `admin` an email address (my canvas → Add Attribute → Email Address, type Official), open
   it and click **Force Verify**, then `workshop mail-test 1`; the message appears in Mailpit.

## Chapter 2: Configuration (result: `02-configuration`)

1. **Configuration → Platform-Wide Configuration → Plugins**: on the **FileConnector** row, gear menu → **Activate**
   ("Plugin Activated"). Same for **PipelineToolkit**. Activation applies the plugin's database schema at once.
   (Command-line equivalent: `workshop cake plugin -a activate -p FileConnector,PipelineToolkit`.)
2. **Platform-Wide Configuration → COs → Add a New CO**, in this order so the ids match the course material:
   Discovery TNG ("Discovery TNG Demo CO"), Redcurrant University ("Redcurrant University Person Registry"),
   Guests ("Guest Registry"), MESS ("Medium Energy Synchrotron Source"). Each new CO gets its default Types, the
   CO:admins / CO:approvers / CO:members:active / CO:members:all / CO:mfaexempt groups (plus their owners groups) and
   CO Settings. `admin` shows as "(Not a Member)": platform admins manage every CO without being a Person in it.
3. In Discovery TNG: **Configuration → Types → Add a New Type**: Attribute `PersonRoles.affiliation_type`, Display
   Name "Principal Investigator", Database Value `principal-investigator`.

## Chapter 3: Connections (result: `03-connections`)

1. In Redcurrant University: **Connections → Pipelines → Add a New Pipeline**: Description "Process HR API Inputs",
   Status Active, Match Strategy **Identifier**, Identifier Type **UID** (appears after choosing Identifier),
   Person Status On Create **Active**, Role Status On Delete **Expired**.
2. **Configuration → API Users → Add a New API User**: type `hr_api_user` (the page adds the `co_3.` prefix itself;
   typing it yourself gives `co_3.co_3.hr_api_user`). Open the user and click **Generate API Key**: the key is shown
   once, and every visit to that page generates a new one.

### Optional: push a person through the API (ApiConnector)

Not part of the checkpoints yet (see question 1 in [laura-alignment.md](laura-alignment.md)); verified working:

1. Activate **ApiConnector** on the Plugins page (COmanage CO).
2. Redcurrant: **Connections → External Identity Sources → Add**: Description "HR API", Status **Manual**, Plugin
   `ApiConnector.ApiSources`, Pipeline "Process HR API Inputs", System of Record Label **`hr`** (required by
   ApiConnector). The next page ("Push Mode, This plugin requires no configuration") has the API source id in its URL
   (`api-connector/api-sources/edit/<ID>`).
3. **Configuration → APIs → Add**: Description "HR API Push", Plugin `ApiConnector.ApiSourceEndpoints`, API User
   `co_3.hr_api_user`; on the next page choose API Source "HR API" and Save. The page then shows the endpoint.
4. Generate the key (chapter 3, step 2), then from the repository directory:

   ```bash
   docker compose exec registry curl -k -i -X PUT -u 'co_3.hr_api_user:<KEY>' \
     -H 'Content-Type: application/json' -H 'Accept: application/json' \
     https://localhost/registry-pe/api/apisource/1/v2/sorPeople/hr/RU-100001 \
     --data-binary '{"sorAttributes":{"names":[{"given":"Avery","family":"Quinlan","type":"official"}],"identifiers":[{"identifier":"aquinlan","type":"uid"}]}}'
   ```

   201 Created the first time, 200 on repeats, 401 with a wrong key; `-X GET` returns the stored record and
   `-X DELETE` removes it. Avery Quinlan appears under **People → My Population**. (Running curl inside the container
   avoids Windows curl differences; from the laptop use `https://localhost:8443/...`.) Body keys: `names`,
   `identifiers`, `emailAddresses` (use `address`, not `mail`), `telephoneNumbers`, `addresses`, `urls`, `roles`
   (needs `roleIdentifier` and `status`), `dateOfBirth`; every list entry needs a `type` that exists in the CO.

## Chapter 4: FileSource (result: `04-filesource-synced`)

1. **Connections → Pipelines → Add**: "Process HR File Inputs", same settings as chapter 3.
2. Open it, click **Flanges** → **Add**: Description "Login identifiers from uid", Status **Build Related Attributes**,
   Plugin `PipelineToolkit.IdentifierMappers`; then **Login Identifier Types → Add**: Type **UID**, **Login** ticked.
   This copies each record's `uid` onto the Person as a login identifier, so participants can log in as
   `ruth.spence`. Without it, file-sourced people cannot log in (CSV v3 cannot carry login identifiers).
3. **Connections → External Identity Sources → Add**: Description "HR File", Status **Full** (never leave it
   Disabled: syncing a Disabled source throws a TypeError in 5.2.0), Plugin `FileConnector.FileSources`, Pipeline
   "Process HR File Inputs", System of Record Label `hr`. Saving opens the File Source form: File Name
   `/srv/comanage-registry/local/filesource/hr.csv`, File Format **CSV v3**, leave Archive Directory empty.
4. Full sync, from the command line (5.2.0 has no UI button for it):
   `workshop sync 3 1` → `Job 1: OK - Sync Finished (45 new, 0 updated, 0 errors, 45 total)` in about five seconds.
   Show the result under **Operations → Jobs** (the job's history records) and **People → My Population**.
5. One record at a time in the UI: **External Identity Sources → HR File → Search Source**, search `Spence`, click
   the SORID → the retrieved record (raw CSV row included) → **Sync Record to CO** ("External Identity Source sync
   complete").
6. Log in as `ruth.spence` in a private window: she lands on Redcurrant University's dashboard as herself.

Exercise: add a second source for `registrar.csv` (same pipeline). Its 45 people are different from `hr.csv`'s.

## Chapter 5: Organisational structure (result: `05-org-structure`)

Redcurrant University:

1. **Structure → COUs → Add a New COU**: Alumni ("Alumni of the student body"), Faculty/Staff ("Active faculty and
   administration"), Retirees ("Former faculty/staff"), Students ("Active students"). Each COU gets
   `CO:COU:<name>:admins`, `:approvers`, `:members:active`, `:members:all` (and owners groups).
2. **Structure → Groups → Add a New Group**: `Access-wiki`. Then open `CO:COU:Retirees:members:active` → **Group
   Nestings** → **Add**: Target Group `Access-wiki` ("Where the current group will be nested").
3. **People → My Population → Add**: Lamar Martin (Official name, Active). Add him to CO:admins,
   CO:COU:Faculty/Staff:admins and CO:COU:Retirees:admins (group → **Group Members** → *Add member* picker).
4. Ruth Spence (from the HR file) → **Person Roles → Add**: COU Faculty/Staff, Affiliation Member, Status Active,
   Title "Associate Professor", Department "Biology".
5. Live sequence (not in the checkpoint): set that role's Status to **Expired** → Ruth shows *Expired* and keeps only
   the `members:all` groups; add a second role in COU **Retirees** (Active) → she is Active again, in
   `CO:COU:Retirees:members:active` and, through the nesting, in **Access-wiki**. Memberships update immediately.

Discovery TNG:

6. **Structure → COUs → Add**: `arbovirus`.
7. **People → My Population → Add**: Claude Larkin, Date of Birth 1980-02-18; **Person Roles → Add**: COU arbovirus,
   Affiliation **Principal Investigator** (the type from chapter 2), Title "Principal Investigator". He ends up in four
   groups: CO:members:active/all and CO:COU:arbovirus:members:active/all.
8. **Structure → Groups → CO:mfaexempt** → Description "MFA Exemptions".

## Chapter 6: Enrollment (result: `06-enrollment`)

The flow in the checkpoint is Discovery TNG's **"Join Discovery TNG"**: anyone who logs in can sign up, verifies
their email with a code from Mailpit, and gets a login identifier and a role in COU arbovirus.

1. **Configuration → Message Templates → Add**, twice (Status Active, Format Plain Text):
   - "Discovery TNG Email Verification", Context **Verification**, Subject `(@CO_NAME) email verification code`, body
     containing `(@VERIFICATION_CODE)`.
   - "Discovery TNG Welcome", Context **Enrollment Finalization**, Subject `Welcome to (@CO_NAME)`, body using
     `(@ENROLLEE_NAME)` and `(@ENROLLEE_EMAIL)`.
   Substitutions are written `(@NAME)`; no `<` or `>` in the plain text.
2. **People → Enrollment Flows → Add**: Name "Join Discovery TNG", Petitioner Authorization **Any Authenticated
   User**, **Collect Enrollee Email** ticked (without it the welcome mail is never sent), Finalization Message
   Template "Discovery TNG Welcome".
3. **Enrollment Flow Steps → Add**, each with Actor Type **Enrollee**:
   1. "About You": `CoreEnroller.BasicAttributeCollectors`; Name Type Official, Email Address Type Personal,
      Affiliation Type Affiliate, COU arbovirus.
   2. "Verify Your Email Address": `CoreEnroller.EmailVerifiers`; Mode **One**, Message Template "Discovery TNG Email
      Verification", Request Validity **60** (required, only a placeholder is shown), untick Enable Attempt Blocker.
   3. "Link Your Login": `CoreEnroller.IdentifierCollectors`; Type **Network**. It has no page: it records the
      username the enrollee logged in with as their login identifier.
4. Run it as a new person: copy the flow's **Start** link (`https://localhost:8443/registry-pe/enrollment-flows/start/1`),
   open a private window, log in as e.g. `pat.newcomer` (blank password), enter an email address, fill About You
   (same email), **Verify** → the code arrives in Mailpit → enter it → **Verify Email** → **Finish** →
   "Enrollment Complete". The welcome mail follows. Logging in again as `pat.newcomer` lands in Discovery TNG.
   Each username can enrol once per database. **Never click Start as `admin`**: it would record admin as the enrollee.
5. As `admin`: **People → Petitions** (status Finalized, the collected data, the history).

### Optional: add approval

An approver must be a Person **in that CO** with a login identifier and a verified email (`admin` cannot approve:
it is not a Discovery TNG Person). For example Claude Larkin: add an Identifier `claude.larkin` (type Network, Login
ticked), an Email Address (Force Verify), and membership of CO:approvers. Then add a Message Template with Context
**Enrollment Handoff** (body with `(@ENTRY_URL)`), and a fourth step: `CoreEnroller.ApprovalCollectors`, Actor Type
**Approver**, Handoff Message Template = that template. The Approver Group field only appears on the step's Edit
page (a 5.2.0 bug); without it the CO's (or the petition COU's) approvers group is used. The enrollee then waits at
"handoff", Claude gets an email with the link, approves in his own window, and the enrollee gets the welcome mail.

## Laura's CSV files

- Put them in `image/data/filesource/` (they appear at `/srv/comanage-registry/local/filesource/`). With the author
  overlay (`docker compose -f compose.yaml -f compose.author.yaml up -d`) edits are live: the file is re-read on every
  sync. Rebuild the image to ship them.
- **CSV v3 rules** (5.2.0): first column header exactly `SORID`; other headers `names.given.official`,
  `names.family.official`, `email_addresses.mail.official`, `identifiers.identifier.uid`, ... (`model.field.type`,
  lowercase, the type must exist in the CO); roles as `external_identity_roles.1.affiliation`,
  `...1.title`, `...1.status` (A, S, D, GP, D2); UTF-8 **without BOM**, no `<` or `>`, unique SORIDs without leading
  zeros (Excel likes to mangle long numbers), `YYYY-MM-DD HH:MM:SS` dates. No `identifiers.login.*` (use the flange).
- v4-style files (like Shayna's) convert with `python3 tools/convert_v4_csv.py IN.csv OUT.csv --uid`.
- Only fictional people. Rows deleted from the file are **not** processed in 5.2.0.

## Regenerating the checkpoints

```bash
make build                       # image from this checkout
tools/seed/seed-all.sh           # all six (about five minutes); or e.g. "tools/seed/seed-all.sh 05" for 05-06
make build                       # bake the new dumps into the image
```

`seed-all.sh` drives the same screens as above with Playwright (in a container; nothing to install) and calls the
`workshop` CLI for the command-line steps. Values live in `tools/seed/seed.py`. To save a hand-made state instead:
`workshop checkpoint 07-my-demo "what it contains"` with the author overlay running.

## Known 5.2.0 traps

| Trap | What to do |
|---|---|
| Logged in but not authorized → endless redirect (ERR_TOO_MANY_REDIRECTS) with `DEBUG=false` | Go to `/registry-pe/` or log out; set `DEBUG=true` on the demo machine for a flash message instead |
| Full FileSource sync is command-line only | `workshop sync 3 1` |
| Syncing a source whose Status is Disabled → TypeError | Use Full (or Manual/Update) |
| Rows removed from the CSV are never processed (the sync logs an error per missing key) | Demonstrate leavers by role status, not by deleting rows |
| `bin/cake job -r -c all` fails | The kit's job runner loops over CO ids for you |
| Mail sent by command-line jobs has links without a host | Trigger mail from the UI |
| Generate API Key regenerates on every visit | Copy the key from the first page |
| Force Verify on an address that is already verified → HTTP 500 | Check the Verified column first |
| A step that changes actor without a Handoff Message Template stops the flow | Always set one on approval steps |
| A notification recipient without a verified email → HTTP 500 for the enrollee | Force-verify approvers' email first |
| Basic credentials are cached by the browser | Private windows, or `127.0.0.1` vs `localhost`, per persona |

## When something goes wrong

- `docker compose ps` (health), `workshop status` (processes), `docker compose logs registry | grep -v ' debug: '`
  (web requests and start-up), `workshop logs` (command-line and job runner errors), `workshop psql` (database).
- Lost the plot: `workshop restore <checkpoint>`. Lost the container: `docker compose down && docker compose up -d`.
