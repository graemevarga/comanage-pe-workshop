"""Walk through workshop procedures by driving the Registry UI like a participant would.

Run through tools/seed/seed-all.sh, which resets the kit (a fresh install, as participants start), runs each stage
here and saves a checkpoint after each one. Stage N expects the state after stage N-1.  Usage: python seed.py STAGE
The current stages follow the procedures in docs/instructor-guide.md (values from Laura Paglione's early
screenshots); rewrite them to follow the lesson plan.
"""
import re
import sys

from registry import Registry, RegistryError, sync_playwright

COS = [  # created in this order on a fresh install, so the ids are 2..5 like the course material
    ("Discovery TNG", "Discovery TNG Demo CO"),
    ("Redcurrant University", "Redcurrant University Person Registry"),
    ("Guests", "Guest Registry"),
    ("MESS", "Medium Energy Synchrotron Source"),
]
SMTP_SERVER = "Mailpit (workshop mail catcher)"


def co_id(r, name):
    """Find a CO id from the platform CO list."""
    r.go("cos?co_id=1")
    for a in r.page.locator("main a").all():
        if a.inner_text().strip() == name:
            m = re.search(r"/cos/edit/(\d+)", a.get_attribute("href") or "")
            if m:
                return int(m.group(1))
    raise RegistryError(f"CO {name!r} not found")


def co_settings(r, co):
    """Open the CO's settings form (the CO Settings link on the Configuration menu page)."""
    r.go(f"dashboards/configuration?co_id={co}")
    href = r.page.locator("a", has_text="CO Settings").first.get_attribute("href")
    r.go(href)


def activate_plugin(r, plugin):
    r.go("plugins?co_id=1")
    row = r.page.locator("tr", has_text=plugin).first
    if "Active" in row.inner_text().split(plugin, 1)[1]:
        print(f"  {plugin} already active")
        return
    row.locator(".action-menu-toggle").click()
    row.locator("a.dropdown-item", has_text="Activate").click()
    r.page.wait_for_load_state("networkidle")
    r.assert_ok(f"activate {plugin}")
    print(f"  activated {plugin}: {r.flashes()}")


# ---- 01-email: the setup step's Outgoing SMTP Server shows in the UI; the admin gets a verified address ---------
def stage_01(r):
    # workshop-setup (setup/mail.sql) inserted the server; check the UI sees it the way it sees one it made itself.
    r.go("servers/index?co_id=1")
    if SMTP_SERVER not in r.page.content():
        raise RegistryError(f"{SMTP_SERVER!r} not in the COmanage CO's servers")
    r.shot("smtp-server")
    co_settings(r, 1)
    chosen = r.page.locator('form select[name="email_smtp_server_id"] option:checked').inner_text().strip()
    if chosen != SMTP_SERVER:
        raise RegistryError(f"CO Settings > Outgoing SMTP Server is {chosen!r}")
    r.shot("co-settings")
    # A verified address for the platform admin (Person 1), so "workshop mail-test 1" works straight away
    r.go("email-addresses/add?person_id=1")
    r.fill({"mail": "admin@workshop.test", "type_id": {"label": "Official"}})
    r.save("admin email address")
    email_id = r.id_from_url()
    r.go(f"email-addresses/force-verify/{email_id}")
    if not any("force verified" in f for f in r.flashes()):
        raise RegistryError(f"force verify failed: {r.flashes()}")


# ---- 02-configuration: plugins, the four demo COs, a custom affiliation type ------------------------------------
def stage_02(r):
    for plugin in ("FileConnector", "PipelineToolkit"):
        activate_plugin(r, plugin)
    r.go("plugins?co_id=1")
    r.shot("plugins")
    for name, description in COS:
        r.go("cos/add?co_id=1")
        r.fill({"name": name, "description": description, "status": "A"})
        r.save(f"add CO {name}")
    ids = {name: co_id(r, name) for name, _ in COS}
    print("  CO ids:", ids)
    if [ids[n] for n, _ in COS] != [2, 3, 4, 5]:
        raise RegistryError(f"unexpected CO ids {ids}; start from a fresh install")
    r.shot("cos")
    # Discovery TNG: custom Person Role affiliation used by Claude Larkin's role later
    r.go("types/add?co_id=2")
    r.fill({"attribute": "PersonRoles.affiliation_type", "display_name": "Principal Investigator",
            "value": "principal-investigator", "status": "A"})
    r.save("add affiliation type Principal Investigator")
    r.go("cos/select")
    r.shot("available-collaborations")


# ---- 03-connections: Redcurrant's pipeline and API user, as in the course material ---------------------------
def stage_03(r):
    r.go("pipelines/add?co_id=3")
    r.fill({"description": "Process HR API Inputs", "status": "A", "match_strategy": "ID"})
    r.set("match_identifier_type_id", {"label": "UID"})
    r.fill({"sync_status_on_create": "A", "sync_status_on_delete": "XP"})
    r.save("add pipeline Process HR API Inputs")
    r.shot("pipeline")
    r.go("api-users/add?co_id=3")
    print("  api user form:", [(f["name"], f["label"]) for f in r.describe_form() if f["visible"]][:3])
    r.fill({"username": "hr_api_user", "status": "A", "privileged": False})
    r.save("add API user hr_api_user")
    r.shot("api-user")
    print("  api user page:", r.page.url, r.flashes())


# ---- 04-filesource-synced (UI part): FileSource for hr.csv; seed-all.sh then runs "workshop sync 3 <eis>" ----------
HR_FILE = "/srv/filesource/hr.csv"


def stage_04(r):
    # A pipeline for the file feed, with the same settings as the course material's "Process HR API Inputs"
    r.go("pipelines/add?co_id=3")
    r.fill({"description": "Process HR File Inputs", "status": "A", "match_strategy": "ID"})
    r.set("match_identifier_type_id", {"label": "UID"})
    r.fill({"sync_status_on_create": "A", "sync_status_on_delete": "XP"})
    r.save("add pipeline Process HR File Inputs")
    pipeline_id = r.page.locator("a", has_text="Process HR File Inputs").first.get_attribute("href").rsplit("/", 1)[1]
    # Flange: copy each record's uid onto the Person as a login identifier, so participants can log in as them
    r.go(f"flanges/add?pipeline_id={pipeline_id}")
    r.fill({"description": "Login identifiers from uid", "status": "MV",
            "plugin": "PipelineToolkit.IdentifierMappers"})
    r.save("add IdentifierMappers flange")
    mapper_href = r.page.locator("a", has_text="Login Identifier Types").first.get_attribute("href")
    r.go(mapper_href.replace("login-identifier-types?", "login-identifier-types/add?"))
    r.fill({"type_id": {"label": "UID"}, "login": True})
    r.save("login identifier type UID")
    # External Identity Source -> FileSource configuration
    r.go("external-identity-sources/add?co_id=3")
    r.fill({"description": "HR File", "status": "F", "plugin": "FileConnector.FileSources",
            "pipeline_id": {"label": "Process HR File Inputs"}, "sor_label": "hr"})
    r.save("add External Identity Source HR File")
    r.fill({"filename": HR_FILE, "format": "C3", "archivedir": "", "threshold_check": ""})
    r.save("configure FileSource")
    eis_id = r.id_from_url()
    print(f"EIS_ID={eis_id}")
    r.shot("eis")


def stage_04_check(r):
    """After the full sync: the course's single-record path (Search Source, Retrieve, Sync Record to CO)."""
    r.go("external-identity-sources?co_id=3")
    r.shot("eis-list")
    r.go("external-identity-sources/edit/1")
    links = r.page.evaluate("() => [...document.querySelectorAll('main a')].map(a => [a.innerText.trim(), a.getAttribute('href')]).filter(x => x[0])")
    print("EIS links:", links)
    r.go("people?co_id=3")
    r.shot("people")


# ---- 05-org-structure: COUs, groups, nesting, hand-made people and roles, as in the course material ---------------
def find_id(r, index_path, text, kind):
    """Id of the row whose link text is exactly `text` on an index page (all rows on one page)."""
    sep = "&" if "?" in index_path else "?"
    r.go(f"{index_path}{sep}limit=100")
    for a in r.page.locator("main table a").all():
        if a.inner_text().strip() == text:
            m = re.search(rf"/{kind}/(?:edit|view)/(\d+)", a.get_attribute("href") or "")
            if m:
                return int(m.group(1))
    raise RegistryError(f"{text!r} not found on {index_path}")


def add_person(r, co, given, family, dob=""):
    r.go(f"people/add?co_id={co}")
    r.fill({"names[0][given]": given, "names[0][family]": family, "names[0][type_id]": {"label": "Official"},
            "status": "A", "date_of_birth": dob})
    r.save(f"add person {given} {family}")
    return r.id_from_url()


def add_role(r, person, fields):
    r.go(f"person-roles/add?person_id={person}")
    r.fill(fields)
    r.save(f"add role {fields.get('title')}")


def add_member(r, co, group, person):
    gid = find_id(r, f"groups?co_id={co}", group, "groups")
    r.go(f"group-members/add?group_id={gid}&person_id={person}")
    r.save(f"add person {person} to {group}")


REDCURRANT_COUS = [
    ("Alumni", "Alumni of the student body"),
    ("Faculty/Staff", "Active faculty and administration"),
    ("Retirees", "Former faculty/staff"),
    ("Students", "Active students"),
]
ARBOVIRUS = ("arbovirus", "Investigation vector-borne determinants of Aedes-transmitted arboviral infections in Cambodia")


def stage_05(r):
    # Redcurrant University (CO 3)
    for name, description in REDCURRANT_COUS:
        r.go("cous/add?co_id=3")
        r.fill({"name": name, "description": description})
        r.save(f"add COU {name}")
    r.go("groups/add?co_id=3")
    r.fill({"name": "Access-wiki", "description": "Access to the wiki", "status": "A",
            "open": False, "nesting_mode_all": False})
    r.save("add group Access-wiki")
    retirees_active = find_id(r, "groups?co_id=3", "CO:COU:Retirees:members:active", "groups")
    r.go(f"group-nestings/add?group_id={retirees_active}")
    r.fill({"target_group_id": {"label": "Access-wiki"}, "negate": False})
    r.save("nest CO:COU:Retirees:members:active into Access-wiki")
    lamar = add_person(r, 3, "Lamar", "Martin")
    for group in ("CO:admins", "CO:COU:Faculty/Staff:admins", "CO:COU:Retirees:admins"):
        add_member(r, 3, group, lamar)
    ruth = find_id(r, "people?co_id=3", "Ruth Spence", "people")
    add_role(r, ruth, {"cou_id": {"label": "Faculty/Staff"}, "affiliation_type_id": {"label": "Member"},
                       "status": "A", "title": "Associate Professor", "department": "Biology"})
    r.go(f"people/edit/{ruth}")
    r.shot("ruth-spence")
    # Discovery TNG (CO 2)
    r.go("cous/add?co_id=2")
    r.fill({"name": ARBOVIRUS[0], "description": ARBOVIRUS[1]})
    r.save("add COU arbovirus")
    claude = add_person(r, 2, "Claude", "Larkin", "1980-02-18")
    add_role(r, claude, {"cou_id": {"label": "arbovirus"}, "affiliation_type_id": {"label": "Principal Investigator"},
                         "status": "A", "title": "Principal Investigator"})
    mfa = find_id(r, "groups?co_id=2", "CO:mfaexempt", "groups")
    r.go(f"groups/edit/{mfa}")
    r.set("description", "MFA Exemptions")
    r.save("CO:mfaexempt description")
    r.go(f"people/edit/{claude}")
    r.shot("claude-larkin")
    print(f"lamar={lamar} ruth={ruth} claude={claude}")


# ---- 06-enrollment: self-signup with email verification in Discovery TNG ---------------------------------------
VERIFY_TEMPLATE = ("Discovery TNG Email Verification", "V", "(@CO_NAME) email verification code", """Hello,

Someone (hopefully you) is enrolling in (@CO_NAME) and asked us to verify this email address.

Your verification code is: (@VERIFICATION_CODE)

Enter this code on the enrollment page within 60 minutes. You may type it with or without the dash.

If you did not request this, you can ignore this message.""")
WELCOME_TEMPLATE = ("Discovery TNG Welcome", "EF", "Welcome to (@CO_NAME)", """Hello (@ENROLLEE_NAME),

Your enrollment in (@CO_NAME) is complete.

Log in to the Registry with the same username you used to enroll.

This message was sent to (@ENROLLEE_EMAIL).""")
FLOW = "Join Discovery TNG"


def add_template(r, co, t):
    description, context, subject, body = t
    r.go(f"message-templates/add?co_id={co}")
    r.fill({"description": description, "status": "A", "context": context, "format": "text",
            "subject": subject, "body_text": body})
    r.save(f"add message template {description}")


def add_step(r, flow, order, description, plugin, config):
    r.go(f"enrollment-flow-steps/add?enrollment_flow_id={flow}")
    r.fill({"description": description, "status": "A", "plugin": plugin, "ordr": str(order), "actor_type": "E"})
    r.save(f"add step {description}")
    r.fill(config)
    r.save(f"configure step {description}")


def stage_06(r):
    add_template(r, 2, VERIFY_TEMPLATE)
    add_template(r, 2, WELCOME_TEMPLATE)
    r.go("enrollment-flows/add?co_id=2")
    r.fill({"name": FLOW, "description": "Self-service sign-up for new Discovery TNG collaborators",
            "status": "A", "authz_type": "AU", "collect_enrollee_email": True,
            "finalization_message_template_id": {"label": WELCOME_TEMPLATE[0]}})
    r.save(f"add enrollment flow {FLOW}")
    flow = r.id_from_url()
    add_step(r, flow, 1, "About You", "CoreEnroller.BasicAttributeCollectors",
             {"name_type_id": {"label": "Official"}, "email_address_type_id": {"label": "Personal"},
              "affiliation_type_id": {"label": "Affiliate"}, "cou_id": {"label": "arbovirus"}})
    add_step(r, flow, 2, "Verify Your Email Address", "CoreEnroller.EmailVerifiers",
             {"mode": "1", "message_template_id": {"label": VERIFY_TEMPLATE[0]}, "request_validity": "60",
              "enable_blockonfailure": False})
    add_step(r, flow, 3, "Link Your Login", "CoreEnroller.IdentifierCollectors", {"type_id": {"label": "Network"}})
    r.go(f"enrollment-flow-steps?enrollment_flow_id={flow}")
    r.shot("flow-steps")
    print(f"FLOW_ID={flow}")


STAGES = {"01": stage_01, "02": stage_02, "03": stage_03, "04": stage_04, "04check": stage_04_check,
          "05": stage_05, "06": stage_06}

if __name__ == "__main__":
    stage = sys.argv[1]
    with sync_playwright() as pw:
        r = Registry(pw, prefix=f"s{stage}-")
        try:
            r.login()
            STAGES[stage](r)
        except Exception:
            r.shot("FAILED")
            raise
        finally:
            r.close()
    print(f"stage {stage} done")
