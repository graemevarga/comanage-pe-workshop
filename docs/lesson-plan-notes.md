# Alignment with the v5.2 course material

How the workshop kit lines up with Laura Paglione's in-progress COmanage Registry PE v5.2 material (57 screenshots in
`InCommon-Training/comanage-files/registry_v5.2`, read on 2026-10-19), and the questions to settle with her.
Everything marked *verified* was checked against the running kit.

The kit runs the 5.2.0 release as delivered (the image upstream's `container/build.sh` builds, PostgreSQL and Mailpit
in their own containers, upstream's default settings), so participants can repeat everything at home. Its only
customisation is anonymous login.

## Already matching (verified)

| Her screenshots | The kit |
|---|---|
| Registry **5.2.0**, stock theme ("COmanage Registry v5.2.0" in the Configuration panel) | Built from the upstream 5.2.0 tag, unmodified |
| Platform admin logs in as **`admin`** | Username `admin`, blank password |
| Five COs: COmanage, **Discovery TNG**, **Redcurrant University**, **Guests**, **MESS**, with her descriptions | Checkpoint `02-configuration`; the "Available Collaborations" page matches hers row for row |
| Discovery TNG = CO 2, Redcurrant = **CO 3** (`co_3.hr_api_user`) | Same ids (COs are created in her order). Even Discovery TNG's "Campus" type is id **51** and its `CO:admins` group id **11**, as in hers |
| Plugins page: FileConnector Active, ApiConnector Suspended | Same (PipelineToolkit is also activated; it is below her crop) |
| Pipeline **"Process HR API Inputs"**: Identifier match on UID, Person Status On Create Active, Role Status On Delete **Expired** | Checkpoint `03-connections`, same values |
| API user **`co_3.hr_api_user`**, Active, not privileged, API key "Not Set" | Same (participants generate the key themselves) |
| Redcurrant COUs **Alumni, Faculty/Staff, Retirees, Students** with her descriptions; group **Access-wiki** fed by nesting **`CO:COU:Retirees:members:active`** | Checkpoint `05-org-structure` |
| **Lamar Martin**: no roles; member of CO:admins, CO:COU:Faculty/Staff:admins, CO:COU:Retirees:admins | Same five group memberships |
| **Ruth Spence**: Associate Professor, Faculty/Staff, Member, Biology; then Expired, then a Retirees role, then Access-wiki through the nesting | Role in `05-org-structure`; the expire-then-Retirees sequence was rehearsed and gives exactly her group lists (memberships update immediately, no job needed) |
| **Claude Larkin** (Discovery TNG): DOB 1980-02-18, Principal Investigator role in COU **arbovirus**, affiliation **Principal Investigator**, 4 groups | Same |
| Discovery TNG `CO:mfaexempt` description "MFA Exemptions" | Same |

## Questions for Laura

0. **URL path.** Her instance serves the app at `/registry-pe/` (`comanage-demo.test.sphericalcloud.net/registry-pe/`);
   the kit uses upstream's default, **`https://localhost:8443/registry/`**, which is also what participants get when
   they install at home. Any text or screenshot that shows `/registry-pe/` will differ. Upstream's build can serve
   `/registry-pe/` instead (`container/build.sh --build-arg COMANAGE_REGISTRY_WEBROOT=registry-pe ...`), so the kit
   can follow her path if she prefers; that means a rebuilt image and updating the paths in the kit's Apache
   configuration and docs.

1. **Is the HR source fed by the API (ApiConnector), by a file (FileSource), or both?**
   Her pipeline name and `co_3.hr_api_user` point to an API push exercise, while Benn asked for FileSource. The kit
   supports both (*verified*):
   - **FileSource** (checkpoint `04-filesource-synced`): a second pipeline "Process HR File Inputs" with the same
     settings, an External Identity Source "HR File" reading `hr.csv`, and a full sync (45 people).
   - **API push**: activate ApiConnector; add an External Identity Source with plugin `ApiConnector.ApiSources`
     (status Manual, System of Record Label `hr`, pipeline "Process HR API Inputs"); add an API (Configuration > APIs)
     with plugin `ApiConnector.ApiSourceEndpoints` for `co_3.hr_api_user`, bound to that source; generate the key;
     then `PUT https://localhost:8443/registry/api/apisource/<id>/v2/sorPeople/hr/<SORID>` with a JSON body
     returned 201 (200 on repeat, 401 with a wrong key). See the instructor guide for the full example.
   Ask: which does the narrative use, in which chapter, and should the API exercise get its own checkpoint?

2. **Person ids differ from hers.** Her Claude Larkin is person 2 and Lamar Martin person 3, because her people were
   made by hand on a database that predates the 5.2.0 tag. In the kit the 45 HR people arrive first (checkpoint 04),
   so Ruth Spence is 45, Lamar Martin 47 and Claude Larkin 48. Ask: does any text depend on ids (for example
   "(ID: 3)")? If so, either avoid ids in the text or move the org-structure chapter before the FileSource sync.
   A `pg_dump` of her instance is the only way to match every id.

3. **Her data.** Ask for her CSV files if they differ from Shayna Atkinson's v4 training population, which the kit
   uses converted to CSV v3 (`hr.csv`, `registrar.csv`, fictional people, with a `uid` column added). Ruth Spence comes
   from `hr.csv`; Lamar Martin is in `registrar.csv` but, as in her screenshots, is created by hand (the kit leaves
   `registrar.csv` unsynced for an exercise).

4. **Logging in.** The kit uses anonymous Basic auth: any username, blank password. `admin` is the platform
   administrator; any other name logs in as whoever has that login identifier, or as a new "authenticated user" with
   no COs (what self-signup needs). The kit also gives every HR person a login identifier from their `uid` (a
   PipelineToolkit flange), so `ruth.spence` lands on her own Redcurrant dashboard. Her "log in" steps need to say
   "type admin, leave the password blank"; to switch persons use a private window or `https://127.0.0.1:8443/registry/`.
   (Upstream's own basic-auth image, which participants will use at home, logs in `registry.admin` with an htpasswd
   password instead.)

5. **The user menu label.** Hers reads "admin" everywhere. In the kit some pages (the CO dashboard, for example) show
   **"Registry Admin"**, the name 5.2.0's setup gives the administrator Person. Cosmetic; it can be renamed if her
   screenshots must match exactly.

6. **Full FileSource sync is command-line only** in 5.2.0: `./workshop sync 3 1` prints
   "Sync Finished (45 new, 0 updated, 0 errors, 45 total)". In the UI, External Identity Sources > HR File >
   Search Source > Retrieve > **Sync Record to CO** syncs one person at a time (*verified*). Which does she document?

7. **FileSource deletes do nothing in 5.2.0** (a removed row makes the sync log an error and leaves the person
   untouched), and "Role Status On Delete" never fires for role-less rows. Demonstrate departures by changing a role's
   status, as her Ruth Spence sequence already does.

8. **Mail.** 5.2 ignores the container's email settings, so a fresh install sends no mail until an Outgoing SMTP
   Server is configured in the UI. In the kit that is the first exercise (Configuration → Servers: host `mailpit`,
   port 1025, no TLS; then CO Settings), saved as checkpoint `01-email`. Does her material cover it? Her enrollment
   chapter should send people to **http://localhost:8025** to read mail. There are no Message Templates until
   someone creates them.

9. **The enrollment chapter.** Her only enrollment screenshot is a blank "Add a New Enrollment Flow" form in
   Discovery TNG, so checkpoint `06-enrollment` is the kit's own design (see the checkpoint table in the README). Ask
   what flow her chapter builds; the checkpoint can be regenerated to match.

10. **Values the kit had to choose** because her screenshots don't show them: the Principal Investigator type's
    database value (`principal-investigator`), Access-wiki's description ("Access to the wiki"), the SMTP server's
    description ("Mailpit (workshop mail catcher)"), and arbovirus's description, which in hers reads "...in Cambodi";
    the kit uses "...in Cambodia".

11. **Time zones.** Her screens show America/New_York or America/Los_Angeles because the Registry uses the browser's
    time zone. Participants will see their own.

12. **Docker Desktop licensing.** Docker Desktop needs a paid subscription for professional use at larger
    organisations and government. Rancher Desktop, Colima and Podman are free alternatives, though none has been
    tested with the kit yet. Worth a line in her prerequisites.

## What changes if her answers differ

Nothing needs redesigning. Every checkpoint is regenerated by `tools/seed/seed-all.sh` (Playwright driving the same
screens she documents) and saved as a file in `checkpoints/`, so new answers mean re-running the seeder and committing
the new dumps. Only a different URL path (question 0) needs a rebuilt image.
