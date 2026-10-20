# Instructor guide

For whoever presents the workshop. Laura Paglione's lesson plan, docs and slides are the script; this guide covers
preparing the kit, checking the lesson plan's procedures against it, presenting, and the 5.2.0 behaviour behind the
procedures. Participants' instructions are in [participant-guide.md](participant-guide.md); how the containers map to
a real deployment is in [design-notes.md](design-notes.md).

Conventions: **Configuration → API Users** means the left navigation's *Configuration* panel, then that link.
`./workshop ...` is run from the repository directory; it prints the `docker compose` command it runs, which is
worth showing on screen: it is the same command participants would use with their own deployment.

## Before the workshop

- [ ] Send participants the [participant guide](participant-guide.md) ("Before the workshop") a week ahead; it has
      them download the images and test the kit at home.
- [ ] Check the lesson plan: run its procedures on a fresh kit (see [Checking the lesson plan](#checking-the-lesson-plan)),
      and save a checkpoint at the start of each chapter on the presenting laptop, so you can jump ahead if a live
      step goes wrong.
- [ ] On the presenting laptop: `docker compose up --wait`, log in as `admin`, open Mailpit.
- [ ] For participants who couldn't download beforehand, bring USB copies of the images:
      `docker save ghcr.io/graemevarga/comanage-registry:5.2.0-basic-auth-1 -o registry-amd64.tar`, and
      `postgres:17` and `axllent/mailpit:v1.31.6` saved once per architecture
      (`docker pull --platform linux/arm64 ...` then `docker save`). Participants run `docker load -i <file>`.
- [ ] Apple Silicon participants run the Registry under emulation: the first start takes longer.
- [ ] Presenting: zoom the browser to 125-150%, use a private window per persona, keep Mailpit in a second tab.

## How the kit fits together

| Where | What |
|---|---|
| `docker compose up --wait` | Starts everything and returns when it is ready. On an empty database it is the Registry's real first start, followed by the `workshop-setup` step |
| `https://localhost:8443/registry/` | The Registry. Login: any username, empty password; `admin` is the platform administrator |
| `http://localhost:8025/` | Mailpit: every message the Registry sends |
| `filesource/` | The CSV files, at `/srv/filesource/` in the registry container (read-only, re-read on every sync) |
| `provisioned/` | File Provisioner output, at `/srv/provisioned/` in the registry container |
| `target-database` | SQL Provisioner target: database `target`, user `target_user`, password `password`, port 5432 (`docker compose exec target-database psql -U target_user -d target`) |
| `./workshop sync <co> <eis>` | Full FileSource sync (command line only in 5.2.0) |
| `./workshop checkpoint NAME` / `restore NAME` / `reset` | Save and restore the Registry database; `reset` = fresh install. A restore doesn't roll back what provisioners already wrote to `provisioned/output.jsonl` or the target database; `reset` empties both |
| `tools/seed/` | Playwright scripts that walk through procedures in the UI (`seed-all.sh`, `topics.py`); screenshots of every step land in `tools/seed/out/` |

## What participants start with

`docker compose up --wait` on an empty database runs the Registry's first start (`bin/cake database` creates the
schema, `bin/cake setup` creates the COmanage CO and the platform administrator `admin`), then the `workshop-setup`
step points the Registry's outgoing mail at Mailpit. Nothing else: no COs, no people, and the plugins are installed
but Suspended. Logging in as `admin` lands on the COmanage CO dashboard ("This is the COmanage CO, which is used for
platform wide configurations.").

## Verified procedures

The procedures below were worked out from Laura's early screenshots and verified on 5.2.0 in this kit. The lesson
plan decides what participants actually do; use these for the click paths and the traps. If you follow them in
order on a fresh install, the ids are: COs COmanage **1**, Discovery TNG **2**, Redcurrant University **3**,
Guests **4**, MESS **5**; External Identity Source "HR File" **1**; the HR people are Person ids 2-46 (in SORID
order), Lamar Martin 47, Claude Larkin 48.

Menu paths, buttons and choices from drop-down lists are in **bold**. Everything you type or paste into a field is
in a code block of its own, so you can copy it with the button GitHub shows on the block.

### Mail (done by the setup step)

The setup step does what the platform administrator would do in the COmanage CO. Show these two pages: they are
what participants will do at home.

1. **Configuration → Servers → Add a New Server**: Status **Active**, Plugin **CoreServer.SmtpServers**, and
   Description:

   ```
   Mailpit (workshop mail catcher)
   ```

   Save. On the next page untick **Use TLS**, leave Username and Password empty, and fill in:
   - Hostname (the compose service name):

     ```
     mailpit
     ```

   - Port:

     ```
     1025
     ```

   - Default From:

     ```
     registry@workshop.test
     ```

   - Default Reply-To:

     ```
     noreply@workshop.test
     ```

   Save.
2. **Configuration → CO Settings** → Outgoing SMTP Server: **Mailpit (workshop mail catcher)** → Save. Set on the
   COmanage CO, it applies to every CO.

To test mail from the command line, the recipient needs a verified address: user menu → **my canvas** → **Add
Attribute** → Email Address, type **Official**:

```
admin@workshop.test
```

Save → **Force Verify** (pressing it again on a verified address gives HTTP 500 in 5.2.0). Then:

```bash
./workshop mail-test 1
```

### Configuration

1. **Configuration → Platform-Wide Configuration → Plugins**: on the **FileConnector** row, gear menu → **Activate**
   ("Plugin Activated"). Same for **PipelineToolkit**, and for **SqlConnector** if the lesson uses the SQL
   Provisioner. Activation applies the plugin's database schema at once. After login, `admin` lands on "Available
   Collaborations" once other COs exist: pick COmanage to see this menu. Command-line equivalent:

   ```bash
   ./workshop cake plugin -a activate -p FileConnector,PipelineToolkit,SqlConnector
   ```

2. **Platform-Wide Configuration → COs → Add a New CO**, four times, in this order so the ids match the course
   material (Name, then Description):

   ```
   Discovery TNG
   ```
   ```
   Discovery TNG Demo CO
   ```

   ```
   Redcurrant University
   ```
   ```
   Redcurrant University Person Registry
   ```

   ```
   Guests
   ```
   ```
   Guest Registry
   ```

   ```
   MESS
   ```
   ```
   Medium Energy Synchrotron Source
   ```

   Each new CO gets its default Types, the CO:admins / CO:approvers / CO:members:active / CO:members:all /
   CO:mfaexempt groups (plus their owners groups) and CO Settings. `admin` shows as "(Not a Member)": platform admins
   manage every CO without being a Person in it.
3. In Discovery TNG: **Configuration → Types → Add a New Type**: Attribute **PersonRoles.affiliation_type**, and
   - Display Name:

     ```
     Principal Investigator
     ```

   - Database Value:

     ```
     principal-investigator
     ```

### Connections

1. In Redcurrant University: **Connections → Pipelines → Add a New Pipeline**: Status **Active**, Match Strategy
   **Identifier**, Identifier Type **UID** (appears after choosing Identifier), Person Status On Create **Active**
   (never leave it blank: every synced record then fails), Role Status On Delete **Expired**, and Description:

   ```
   Process HR API Inputs
   ```

2. **Configuration → API Users → Add a New API User**, Username:

   ```
   hr_api_user
   ```

   The page adds the `co_3.` prefix itself; typing it yourself gives `co_3.co_3.hr_api_user`. Open the user and click
   **Generate API Key**: the key is shown once, and every visit to that page generates a new one.

#### Optional: push a person through the API (ApiConnector)

Verified working:

1. Activate **ApiConnector** on the Plugins page (COmanage CO).
2. Redcurrant: **Connections → External Identity Sources → Add**: Status **Manual**, Plugin
   **ApiConnector.ApiSources**, Pipeline **Process HR API Inputs**, and
   - Description:

     ```
     HR API
     ```

   - System of Record Label (required by ApiConnector):

     ```
     hr
     ```

   The next page ("Push Mode, This plugin requires no configuration") has the API source id in its URL
   (`api-connector/api-sources/edit/<ID>`).
3. **Configuration → APIs → Add**: Plugin **ApiConnector.ApiSourceEndpoints**, API User **co_3.hr_api_user**, and
   Description:

   ```
   HR API Push
   ```

   On the next page choose API Source **HR API** and Save. The page then shows the endpoint.
4. Generate the key (Connections, step 2), then from the repository directory (replace `<KEY>`):

   ```bash
   docker compose exec registry curl -k -i -X PUT -u 'co_3.hr_api_user:<KEY>' \
     -H 'Content-Type: application/json' -H 'Accept: application/json' \
     https://localhost/registry/api/apisource/1/v2/sorPeople/hr/RU-100001 \
     --data-binary '{"sorAttributes":{"names":[{"given":"Avery","family":"Quinlan","type":"official"}],"identifiers":[{"identifier":"aquinlan","type":"uid"}]}}'
   ```

   201 Created the first time, 200 on repeats, 401 with a wrong key; `-X GET` returns the stored record and
   `-X DELETE` removes it. Avery Quinlan appears under **People → My Population**. (Running curl inside the container
   avoids Windows curl differences; from the laptop use `https://localhost:8443/registry/...`.) Body keys: `names`,
   `identifiers`, `emailAddresses` (use `address`, not `mail`), `telephoneNumbers`, `addresses`, `urls`, `roles`
   (needs `roleIdentifier` and `status`), `dateOfBirth`; every list entry needs a `type` that exists in the CO.

### FileSource

1. **Connections → Pipelines → Add**, with the same settings as in Connections step 1, and Description:

   ```
   Process HR File Inputs
   ```

2. Open it, click **Flanges** → **Add**: Status **Build Related Attributes**, Plugin
   **PipelineToolkit.IdentifierMappers**, and Description:

   ```
   Login identifiers from uid
   ```

   Then **Login Identifier Types → Add**: Type **UID**, **Login** ticked. This copies each record's `uid` onto the
   Person as a login identifier, so participants can log in as `ruth.spence`. Without it, file-sourced people cannot
   log in (CSV v3 cannot carry login identifiers).
3. **Connections → External Identity Sources → Add**: Status **Full** (never leave it Disabled: syncing a Disabled
   source throws a TypeError in 5.2.0), Plugin **FileConnector.FileSources**, Pipeline **Process HR File Inputs**,
   and
   - Description:

     ```
     HR File
     ```

   - System of Record Label:

     ```
     hr
     ```

   Saving opens the File Source form: File Format **CSV v3**, leave Archive Directory empty, and File Name:

   ```
   /srv/filesource/hr.csv
   ```

4. Full sync, from the command line (5.2.0 has no UI button for it):

   ```bash
   ./workshop sync 3 1
   ```

   prints `Job N: OK - Sync Finished (45 new, 0 updated, 0 errors, 45 total)` in a few seconds (N is the job's id,
   which counts every job in the Registry, so it is rarely 1). The underlying command, which also works in
   PowerShell, always runs as www-data:

   ```bash
   docker compose exec -u www-data -w /srv/comanage-registry/app registry ./bin/cake job -c 3 -j CoreJob.SyncJob -s external_identity_source_id=1
   ```

   Show the result under **Operations → Jobs** (open the job: the list only says "Started via JobCommand"; the job's
   own page has "Sync Finished ...") and **People → My Population**.
5. One record at a time in the UI: **External Identity Sources → HR File → Search Source**, search for

   ```
   Spence
   ```

   click the SORID → the retrieved record (raw CSV row included) → **Sync Record to CO** ("External Identity Source
   sync complete").
6. Log in as Ruth Spence in a private window (empty password); she lands on Redcurrant University's dashboard as
   herself:

   ```
   ruth.spence
   ```

Exercise: add a second source for `registrar.csv`, the same way as step 3 with the same pipeline, but System of
Record Label `registrar` and File Name:

```
/srv/filesource/registrar.csv
```

Then `./workshop sync 3 2`: 45 more people, with eppn identifiers, who log in with their uid (e.g. `lamar.martin`).
Do it before the organisational structure procedure, which creates Lamar Martin by hand without a uid, so a later
registrar sync makes a second Lamar Martin. Source ids are in the source's URL (`external-identity-sources/edit/N`).

### Organisational structure

Redcurrant University:

1. **Structure → COUs → Add a New COU**, four times (Name, then Description):

   ```
   Alumni
   ```
   ```
   Alumni of the student body
   ```

   ```
   Faculty/Staff
   ```
   ```
   Active faculty and administration
   ```

   ```
   Retirees
   ```
   ```
   Former faculty/staff
   ```

   ```
   Students
   ```
   ```
   Active students
   ```

   Each COU gets `CO:COU:<name>:admins`, `:approvers`, `:members:active`, `:members:all` (and owners groups).
2. **Structure → Groups → Add a New Group**, Name (and, optionally, Description "Access to the wiki"):

   ```
   Access-wiki
   ```

   Then open **CO:COU:Retirees:members:active** → **Group Nestings** → **Add**: Target Group **Access-wiki** ("Where
   the current group will be nested").
3. **People → My Population → Add**: Status **Active**, Name type **Official**, Given Name and Family Name:

   ```
   Lamar
   ```
   ```
   Martin
   ```

   Add him to **CO:admins**, **CO:COU:Faculty/Staff:admins** and **CO:COU:Retirees:admins** (group → **Group
   Members** → *Add member* picker: type `Martin`, pick him; the dialog stays open after Save, close it).
4. Ruth Spence (from the HR file) → **Person Roles → Add**: COU **Faculty/Staff**, Affiliation **Member**, Status
   **Active**, and
   - Title:

     ```
     Associate Professor
     ```

   - Department:

     ```
     Biology
     ```

5. Live sequence: set that role's Status to **Expired** → Ruth shows *Expired* and keeps only the `members:all`
   groups; add a second role in COU **Retirees** (Active) → she is Active again, in
   `CO:COU:Retirees:members:active` and, through the nesting, in **Access-wiki**. Memberships update immediately.

Discovery TNG:

6. **Structure → COUs → Add**, Name and Description:

   ```
   arbovirus
   ```
   ```
   Investigation vector-borne determinants of Aedes-transmitted arboviral infections in Cambodia
   ```

7. **People → My Population → Add**: Status **Active**, Name type **Official**, Given Name, Family Name and Date of
   Birth:

   ```
   Claude
   ```
   ```
   Larkin
   ```
   ```
   1980-02-18
   ```

   Then **Person Roles → Add**: COU **arbovirus**, Affiliation **Principal Investigator** (the type from
   Configuration step 3), Title:

   ```
   Principal Investigator
   ```

   He ends up in four groups: CO:members:active/all and CO:COU:arbovirus:members:active/all.
8. **Structure → Groups → CO:mfaexempt** → Description:

   ```
   MFA Exemptions
   ```

### Enrollment: self-signup

Discovery TNG's **"Join Discovery TNG"**: anyone who logs in can sign up, verifies their email with a code from
Mailpit, and gets a login identifier and a role in COU arbovirus.

1. **Configuration → Message Templates → Add**, twice, each with Status **Active** and Format **Plain Text**.
   Substitutions are written `(@NAME)`; no `<` or `>` in plain text.
   - Context **Verification**. Description, Subject, Message Body:

     ```
     Discovery TNG Email Verification
     ```
     ```
     (@CO_NAME) email verification code
     ```
     ```
     Hello,

     Someone (hopefully you) is enrolling in (@CO_NAME) and asked us to verify this email address.

     Your verification code is: (@VERIFICATION_CODE)

     Enter this code on the enrollment page within 60 minutes. You may type it with or without the dash.

     If you did not request this, you can ignore this message.
     ```

   - Context **Enrollment Finalization**. Description, Subject, Message Body:

     ```
     Discovery TNG Welcome
     ```
     ```
     Welcome to (@CO_NAME)
     ```
     ```
     Hello (@ENROLLEE_NAME),

     Your enrollment in (@CO_NAME) is complete.

     Log in to the Registry with the same username you used to enroll.

     This message was sent to (@ENROLLEE_EMAIL).
     ```

2. **People → Enrollment Flows → Add**: Status **Active**, Petitioner Authorization **Any Authenticated User**,
   **Collect Enrollee Email** ticked (without it the welcome mail is never sent), Finalization Message Template
   **Discovery TNG Welcome**, and Name:

   ```
   Join Discovery TNG
   ```

3. **Enrollment Flow Steps → Add**, three times, each with Actor Type **Enrollee** (Description, then the plugin's
   settings):
   1. Plugin **CoreEnroller.BasicAttributeCollectors**; Name Type **Official**, Email Address Type **Personal**,
      Affiliation Type **Affiliate**, COU **arbovirus**:

      ```
      About You
      ```

   2. Plugin **CoreEnroller.EmailVerifiers**; Mode **One**, Message Template **Discovery TNG Email Verification**,
      untick Enable Attempt Blocker, and Request Validity (required, though only a placeholder is shown):

      ```
      Verify Your Email Address
      ```
      ```
      60
      ```

   3. Plugin **CoreEnroller.IdentifierCollectors**; Type **Network**. It has no page: it records the username the
      enrollee logged in with as their login identifier.

      ```
      Link Your Login
      ```

4. Run it as a new person: copy the flow's **Start** link, open a private window, and paste it:

   ```
   https://localhost:8443/registry/enrollment-flows/start/1
   ```

   Log in as a new username (empty password), for example

   ```
   pat.newcomer
   ```

   enter an email address, fill About You (same email), **Verify** → the code arrives in Mailpit → enter it →
   **Verify Email** → **Finish** → "Enrollment Complete". The welcome mail follows. Logging in again as
   `pat.newcomer` lands in Discovery TNG. Each username can enrol once per database. **Never click Start as
   `admin`**: it would record admin as the enrollee.
5. As `admin`: **People → Petitions** (status Finalized, the collected data, the history).

#### Optional: add approval

An approver must be a Person **in that CO** with a login identifier and a verified email (`admin` cannot approve:
it is not a Discovery TNG Person). For example Claude Larkin: add an Identifier (type **Network**, **Login** ticked)

```
claude.larkin
```

an Email Address (Force Verify), and membership of CO:approvers. Then add a Message Template with Context
**Enrollment Handoff** (body with `(@ENTRY_URL)`), and a fourth step: **CoreEnroller.ApprovalCollectors**, Actor
Type **Approver**, Handoff Message Template = that template. The Approver Group field only appears on the step's
Edit page (a 5.2.0 bug); without it the CO's (or the petition COU's) approvers group is used. The enrollee then
waits at "handoff", Claude gets an email with the link, approves in his own window, and the enrollee gets the
welcome mail.

### Provisioning: File Provisioner

Verified in Redcurrant University after the FileSource procedure (`tools/seed/topics.py`, stage `file`).

1. **Connections → Provisioning Targets → Add a New Provisioning Target**: Provisioning Mode **Disabled** (the
   default, Queue on Error, is a trap: see below), Plugin **FileConnector.FileProvisioners**, leave the rest, and
   Description:

   ```
   File Export
   ```

   Save. The "Configure FileProvisioners" page has one field, File Name:

   ```
   /srv/provisioned/output.jsonl
   ```

   Save. (A file that doesn't exist is refused: 'The file "..." is not writable'; the kit creates this one.)
2. Back on the target (PROPERTIES tab): Provisioning Mode **Immediate** → Save. Switching writes nothing by itself.
3. Open `provisioned/output.jsonl` on the laptop, or follow it in a terminal:

   ```bash
   tail -f provisioned/output.jsonl
   ```

   Every change to a person appends one JSON line per event, the whole person record (names, identifiers, roles,
   group memberships, with every type and group nested: about 6.7 KB a line). Changing Ruth Spence's role title adds
   one line; expiring her only role makes her ineligible and writes `{"id":45}`; adding someone to a group also
   writes the group.
4. **People already in the Registry are not written until something about them changes.** To push one person:
   person page → gear by the name → **Provisioning Status** → row gear → **Provision Now** → confirm. There is no
   flash; Last Status becomes "Provisioned", Last Comment "Wrote 1 record to file". To push everyone:
   **Provisioning Targets** → row gear → **Reprovision All** (no confirmation; "Reprovisioning for People, Groups
   queued for File Export (N)"). That only queues two jobs (Operations → Jobs); the kit has no queue runner, so run
   it:

   ```bash
   ./workshop cake job -r -c 3
   ```

   or, from PowerShell:

   ```bash
   docker compose exec -u www-data -w /srv/comanage-registry/app registry ./bin/cake job -r -c 3
   ```

   The People job writes 45 lines ("Reprovisioned 45 entities"); the Groups job reports 0 entities (a 5.2.0 bug).

### Provisioning: SQL Provisioner

Verified after the File Provisioner (`topics.py`, stage `sql`). SqlConnector must be active (Configuration step 1).

1. **Connections → Related Configurations → Servers** (also Configuration → Servers) → **Add a New Server**:
   Status **Active**, Plugin **CoreServer.SqlServers**, and Description:

   ```
   Target Database
   ```

   Save. On "Configure SqlServers": RDBMS Type **Postgres**, Port empty, and
   - Hostname:

     ```
     target-database
     ```

   - Database Name:

     ```
     target
     ```

   - Username:

     ```
     target_user
     ```

   - Password:

     ```
     password
     ```

   Save.
2. **Provisioning Targets → Add**: Mode **Disabled**, Plugin **SqlConnector.SqlProvisioners**, and Description:

   ```
   SQL Export
   ```

   Save. On "Configure SqlProvisioners": Server **Target Database**, Table Name Prefix `sp_` (already filled in) →
   Save. Saving creates 15 tables in the target database (`sp_people`, `sp_names`, `sp_identifiers`,
   `sp_person_roles`, `sp_groups`, `sp_group_members`, `sp_types`, ...) and copies the reference data (Types, COUs,
   Groups). The CONFIGURE PLUGIN tab also has **Reapply Target Database Schema** and **Resync Reference Data**.
3. Set the target's Mode to **Immediate**. Provisioning works as for the file: changes go out at once, Provision Now
   shows Last Comment "New record published", Reprovision All needs the job run above.
4. Look at the result. Open psql on the target database:

   ```bash
   docker compose exec target-database psql -U target_user -d target
   ```

   then list the tables with `\dt`, and query them:

   ```sql
   select p.id, p.status, n.given, n.family, i.identifier as login, r.title
   from sp_people p join sp_names n on n.person_id = p.id and n.primary_name
   left join sp_identifiers i on i.person_id = p.id and i.login
   left join sp_person_roles r on r.person_id = p.id
   order by n.family, n.given limit 5;
   ```

   (`\q` quits.) The `sp_` ids are the Registry's ids. Each HR person has two names in `sp_names`, as in the
   Registry: the primary name and the copy linked to the HR record.

### Enrollment: invitation

Verified in Redcurrant University (`topics.py`, stage `invite`): a CO administrator invites someone by email; the
invitee accepts from the link in Mailpit, logs in with a new username, and becomes a Person in the CO.

1. **Who invites.** Only Any Authenticated User and **CO Administrator** flows exist in 5.2.0, and an invitation
   needs CO Administrator. The platform administrator can't start such a flow in a CO where it isn't a Person (the
   browser ends in "too many redirects"), so the inviter must be a Person in the CO with a login identifier, in
   CO:admins. With the FileSource procedure done, Ruth Spence is the quickest: **Structure → Groups → CO:admins →
   GROUP MEMBERS → Add member**, type

   ```
   Spence
   ```

   and pick Ruth Spence; a "Group Member" dialog opens → Save → close it. Logging in as `ruth.spence` (private
   window) now shows Redcurrant's full menus.
2. **Message Templates** (Configuration → Personalization → **Message Templates** → Add), twice, each with Status
   **Active** and Format **Plain Text**:
   - Context **Enrollment Handoff**. Description, Subject, Message Body (the link is `(@ENTRY_URL)`; there is no
     invitation-specific substitution):

     ```
     Redcurrant Invitation
     ```
     ```
     You are invited to join (@CO_NAME)
     ```
     ```
     Hello (@ENROLLEE_NAME),

     You have been invited to join (@CO_NAME).

     To accept the invitation, open this link:

     (@ENTRY_URL)

     You will be asked to log in. Use the username you want to keep for (@CO_NAME).

     This message was sent to (@ENROLLEE_EMAIL).
     ```

   - Context **Enrollment Finalization**. Description, Subject, Message Body:

     ```
     Redcurrant Welcome
     ```
     ```
     Welcome to (@CO_NAME)
     ```
     ```
     Hello (@ENROLLEE_NAME),

     Your enrollment in (@CO_NAME) is complete.

     Log in to the Registry with the same username you used to accept the invitation.
     ```

3. **People → Enrollment Flows → Add**: Status **Active**, Petitioner Authorization **CO Administrator**, tick
   **Collect Enrollee Email** (off by default; the invitation is sent to this address, not to one collected later),
   Finalization Message Template **Redcurrant Welcome**, and Name:

   ```
   Invite a Member
   ```

4. **Enrollment Flow Steps → Add a New Enrollment Flow Step**, three times (a dialog; Save switches it to the
   plugin's form, and it stays open after the second Save: close it). Description, then the plugin's settings:
   1. Plugin **CoreEnroller.BasicAttributeCollectors**, Actor Type **Petitioner**, Order 1; plugin form: Name Type
      **Official**, Email Address Type **Official**, Affiliation Type **Member**:

      ```
      Enter invitee details
      ```

   2. Plugin **CoreEnroller.InvitationAccepters**, Actor Type **Enrollee**, **Handoff Message Template: Redcurrant
      Invitation** (on the step's own form, not the plugin's), Order 2; plugin form: Invitation Validity and Welcome
      Message. The validity is in **seconds**, although the label says minutes (the default 1440 expires after 24
      minutes); `0` means no expiry.

      ```
      Accept invitation
      ```
      ```
      0
      ```
      ```
      Welcome to Redcurrant University. Please accept your invitation to continue.
      ```

   3. Plugin **CoreEnroller.IdentifierCollectors**, Actor Type **Enrollee**, Order 3; plugin form: Type
      **Network**, and press Save (the step needs its type).

      ```
      Link your login
      ```

5. **Run it.** As `ruth.spence`: People → Enrollment Flows → row gear → **Start** → Enrollee Email, for example

   ```
   casey.invitee@example.org
   ```

   Save → step 1: Given Name, Family Name and Email Address (the same address) → **Continue** → "Enrollment Flow
   Handoff" ("Thank you for completing this Enrollment Flow Step..."). People → Petitions shows it as Pending
   Acceptance.
6. In Mailpit, "You are invited to join Redcurrant University" has the link
   (`https://localhost:8443/registry/petitions/continue/N?token=...`). **Copy it into a new private window** that
   isn't logged in → "Accept this invitation?" → **Accept** → **Continue** → the login prompt: a new username,
   empty password, for example

   ```
   casey.invitee
   ```

   → "Enrollment Complete", flash "Petition Finalized", and the welcome mail arrives. `casey.invitee` now has a
   Network login identifier and lands on Redcurrant's dashboard. If the provisioners are Immediate, Casey is in
   `output.jsonl` and `sp_people` straight away.

Decline instead: the page still says "Enrollment Complete ... has been finalized" with the flash "Invitation
Declined"; the petition is Declined and nobody is mailed.

## Laura's CSV files

- Put them in `filesource/` (mounted read-only at `/srv/filesource/`). Edits are live: the file is re-read on every
  sync. On Linux, keep them world-readable (the web server is uid 33).
- **CSV v3 rules** (5.2.0): first column header exactly `SORID`; other headers `names.given.official`,
  `names.family.official`, `email_addresses.mail.official`, `identifiers.identifier.uid`, ... (`model.field.type`,
  lowercase, the type must exist in the CO); roles as `external_identity_roles.1.affiliation`,
  `...1.title`, `...1.status` (A, S, D, GP, D2); UTF-8 **without BOM**, no `<` or `>`, unique SORIDs without leading
  zeros (Excel likes to mangle long numbers), `YYYY-MM-DD HH:MM:SS` dates. No `identifiers.login.*` (use the flange).
- Windows line endings (CRLF) are fine (verified). A UTF-8 **byte-order mark** is not: every row then fails with
  "Did not find SORID as first defined column, check file header definition" (verified), although the header looks
  right. Excel's "CSV UTF-8" format writes one; save from a text editor (VS Code, Notepad on Windows 11) or Excel's
  plain "CSV (Comma delimited)" for ASCII-only files.
- v4-style files (like Shayna's) convert with `python3 tools/convert_v4_csv.py IN.csv OUT.csv --uid`.
- Only fictional people. Rows deleted from the file are **not** processed in 5.2.0.

## Checking the lesson plan

Laura won't be in the room, so check every procedure in the lesson plan on a fresh kit before the workshop:

1. `./workshop reset` (a fresh install, exactly what participants start with).
2. Follow the lesson plan literally, as a participant would, in a private browser window. Note every place where a
   screen, a label, a value or a result differs from the text, and send those to Laura.
3. At the start of each chapter, `./workshop checkpoint NN-chapter "what is in it"`, so you can restore it while
   presenting.

`tools/seed/` automates this (on Windows, run it from WSL; it needs bash, Docker and, for `topics.py`, Python 3): `seed.py` has one function per stage that drives the same screens with Playwright (in
a container; nothing to install), and `seed-all.sh` runs the stages from a fresh install and saves a checkpoint after
each. `topics.py all --restore` then checks the provisioning and invitation procedures from checkpoint 04 (about 8
minutes; it prints CONFIRMED or REFUTED for each behaviour this guide relies on). The current stages follow the
procedures above; rewrite them to follow the lesson plan, and the run doubles as a regression test when Laura revises
it. Screenshots of every step land in `tools/seed/out/`.

## Known 5.2.0 traps

| Trap | What to do |
|---|---|
| Logged in but not authorized → endless redirect (ERR_TOO_MANY_REDIRECTS) | Go to `/registry/` or log out |
| Full FileSource sync is command-line only | `./workshop sync 3 1` |
| Syncing a source whose Status is Disabled → TypeError | Use Full (or Manual/Update) |
| A pipeline whose "Person Status On Create" is left blank fails every record it syncs | Always choose a status (Active) |
| Rows removed from the CSV are never processed (the sync logs an error per missing key) | Demonstrate leavers by role status, not by deleting rows |
| `bin/cake job -r -c all` fails | One `-c <co_id>` per CO |
| `bin/cake` run as root leaves root-owned cache files that break the web server | Always `docker compose exec -u www-data ...` (`./workshop cake` does) |
| Every registry start logs `cannot drop index format_assigner_sequences_i1` | Harmless; the entrypoint's schema re-run isn't idempotent for CoreAssigner |
| Mail sent by command-line jobs has links without a host | Trigger mail from the UI |
| Generate API Key regenerates on every visit | Copy the key from the first page |
| Force Verify on an address that is already verified → HTTP 500 | Check the Verified column first |
| A step that changes actor without a Handoff Message Template stops the flow | Always set one on approval steps |
| A notification recipient without a verified email → HTTP 500 for the enrollee | Force-verify approvers' email first |
| Basic credentials are cached by the browser | Private windows, or `127.0.0.1` vs `localhost`, per persona |
| A provisioning target whose plugin form (File Name, Server) was never saved, in any mode but Disabled → **every person save in the CO returns HTTP 500** | Create targets as Disabled, configure the plugin, then switch to Immediate. To remove a broken one: target → PROPERTIES → Delete |
| People already in the Registry aren't provisioned | They go out when they change; or Provision Now per person; or Reprovision All plus `./workshop cake job -r -c <co_id>` |
| Reprovision All's Groups job reports "0 entities" | 5.2.0 bug; groups still go out when they or their members change |
| `admin` starting a CO Administrator flow → too many redirects | Invite as a CO administrator who is a Person in the CO (e.g. Ruth Spence in CO:admins) |
| Invitation Validity is in seconds (the label says minutes) | `0` for no expiry; it is checked when the invitee replies, so raising it revives an expired invitation |
| Opening an invitation link in a logged-in browser → 403, and the petition is now bound to that user | Always open invitation links in a fresh private window. Recover: People → Petitions → View → Terminate, and invite again |
| Reopening a used (accepted or declined) invitation link → HTTP 500 | Expected; the petition is complete |
| "Add member" and "Add a New Enrollment Flow Step" dialogs stay open after Save | Close them with X |

## When something goes wrong

- `docker compose ps` (health), `docker compose logs registry | grep -v ' debug: '` (web requests and start-up),
  `./workshop psql` (database). `COMANAGE_DEBUG=1` on the registry service shows the entrypoint's start-up output
  (and turns on CakePHP debug mode).
- Lost the plot: `./workshop restore <checkpoint>` (one you saved; provisioner output isn't rolled back). Start
  over: `./workshop reset`.
