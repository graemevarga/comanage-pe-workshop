#!/usr/bin/env python3
"""Check three lesson topics in the Registry UI, the way a participant does them: a File Provisioner, a SQL
Provisioner, and an enrollment flow that invites someone by email. Each claim the lesson relies on is printed as
CONFIRMED or REFUTED with the evidence, and a summary closes the run.

Start from checkpoint 04 (HR file synced into Redcurrant University) and run the stages in order, on the host, from
the repository directory:

    ./workshop restore 04-filesource-synced
    python3 tools/seed/topics.py all          # plugins, file, sql, invite;  "all --restore" restores first
    python3 tools/seed/topics.py file         # or one stage at a time, in that order

The host side runs the command-line steps (the job queue as www-data, psql on the target database, reading
provisioned/output.jsonl, Mailpit); the browser steps run in the Playwright container (tools/seed/pw topics.py ui
PART ...), like seed.py. The file and sql stages empty provisioned/output.jsonl and drop the sp_ tables in the
target database first, so a rerun after a restore starts clean. Screenshots: tools/seed/out/t-*.png.
"""
import copy
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CO = 3  # Redcurrant University
OUTPUT_HOST = REPO / "provisioned" / "output.jsonl"
OUTPUT = "/srv/provisioned/output.jsonl"  # the same file, as the Registry sees it
APP = "/srv/comanage-registry/app"
IN_UI = False  # set when run as "topics.py ui PART" in the Playwright container

RESULTS = []


def record(claim, ok, evidence):
    """ok: True (CONFIRMED), False (REFUTED) or a verdict string such as "NOTE"."""
    verdict = ok if isinstance(ok, str) else ("CONFIRMED" if ok else "REFUTED")
    evidence = " ".join(str(evidence).split())
    if IN_UI:
        print(f"@@CHECK\t{claim}\t{verdict}\t{evidence}", flush=True)
    else:
        RESULTS.append((claim, verdict, evidence))
        print(f"  [{verdict}] {claim}: {evidence}", flush=True)


def var(key, value):
    print(f"@@VAR\t{key}\t{value}", flush=True)


# =====================================================================================================================
# Host side
# =====================================================================================================================
def run(cmd, check=True):
    p = subprocess.run(cmd, cwd=REPO, text=True, capture_output=True)
    if check and p.returncode != 0:
        sys.exit(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
    return p.stdout


def rsql(query):
    """Query the Registry database."""
    return run(["docker", "compose", "exec", "-T", "registry-database", "psql", "-U", "registry_user", "-d",
                "registry", "-Atqc", query]).strip()


def tsql(query, pretty=False):
    """Query the SQL Provisioner's target database, as a participant would with psql."""
    return run(["docker", "compose", "exec", "-T", "target-database", "psql", "-U", "target_user", "-d", "target",
                *([] if pretty else ["-Atq"]), "-c", query]).rstrip()


def run_jobs():
    print(f"  $ ./workshop cake job -r -c {CO}      (runs the CO's queued jobs, as www-data)")
    run(["docker", "compose", "exec", "-T", "-u", "www-data", "-w", APP, "registry", "env", "-u",
         "COMANAGE_REGISTRY_CONTAINER", "./bin/cake", "job", "-q", "-r", "-c", str(CO)])


def ui(part, *args):
    """Run a browser part in the Playwright container; returns the @@VAR values it printed."""
    print(f"  -- browser: {part} {' '.join(map(str, args))}".rstrip(), flush=True)
    p = subprocess.Popen([str(HERE / "pw"), "topics.py", "ui", part, *map(str, args)], cwd=REPO, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    found = {}
    for line in p.stdout:
        line = line.rstrip("\n")
        if line.startswith("@@CHECK\t"):
            _, claim, verdict, evidence = line.split("\t", 3)
            record(claim, verdict, evidence)
        elif line.startswith("@@VAR\t"):
            _, k, v = line.split("\t", 2)
            found[k] = v
        else:
            print("     " + line, flush=True)
    if p.wait() != 0:
        sys.exit(f"browser part '{part}' failed; see the screenshots in tools/seed/out/t-*FAILED*.png")
    return found


def need(ok, what):
    if not ok:
        sys.exit(f"precondition failed: {what}.\nStart from: ./workshop restore 04-filesource-synced, then run the "
                 f"stages in order (plugins file sql invite), or: python3 tools/seed/topics.py all --restore")


def header(text):
    print(f"\n=== {text} ===", flush=True)


def output_lines():
    with open(OUTPUT_HOST, encoding="utf-8") as f:
        return f.read().splitlines()


def kinds(lines):
    """One short description per provisioned JSON line."""
    out = []
    for line in lines:
        d = json.loads(line)
        if list(d) == ["id"]:
            out.append(json.dumps(d, separators=(",", ":")))
        elif "group_type" in d:
            out.append(f"group {d['id']} {d.get('name')}")
        else:
            name = d.get("primary_name") or {}
            label = f"{name.get('given', '')} {name.get('family', '')}".strip() or "no name yet"
            out.append(f"person {d['id']} ({label}, status {d.get('status')})")
    return out


def trimmed(line):
    """A provisioned person line, cut down to what is worth showing on a slide."""
    d = json.loads(line)
    keep = {k: d.get(k) for k in ("id", "co_id", "status", "date_of_birth", "modified")}
    keep["primary_name"] = {k: (d.get("primary_name") or {}).get(k) for k in ("given", "family", "type_id")}
    keep["identifiers"] = [{k: i.get(k) for k in ("identifier", "type_id", "login")} for i in d.get("identifiers", [])]
    keep["person_roles"] = [{k: i.get(k) for k in ("title", "department", "affiliation_type_id", "status")}
                            for i in d.get("person_roles", [])]
    keep["group_members"] = [i.get("group_id") for i in d.get("group_members", [])]
    keep["..."] = f"{len(line)} bytes in full, every type and group nested as a whole record"
    return json.dumps(keep)


def person_id_by_login(login):
    return rsql(f"select person_id from identifiers where identifier = '{login}' and login is true "
                f"and identifier_id is null and deleted is not true and person_id is not null limit 1")


def live_targets():
    return rsql(f"select count(*) from provisioning_targets where co_id = {CO} and provisioning_target_id is null "
                f"and deleted is not true")


def queued_provisioner_jobs():
    rows = rsql("select id, parameters, register_summary from jobs where job_id is null and status = 'Q' "
                "and plugin = 'CoreJob.ProvisionerJob' order by id")
    return [r.split("|", 2) for r in rows.splitlines() if r]


def job_summaries(jobs):
    """{model: 'status: finish summary'} for the jobs returned by queued_provisioner_jobs()."""
    rows = dict(r.split("|", 1) for r in rsql(
        "select id, coalesce(status, '') || ': ' || coalesce(finish_summary, '') from jobs where id in (%s)"
        % ",".join(j[0] for j in jobs)).splitlines())
    return {json.loads(j[1])["model"]: rows[j[0]] for j in jobs}


def registry_log_since(since, needle):
    out = run(["docker", "compose", "logs", "--no-log-prefix", "--since", since, "registry"], check=False)
    return [line.strip() for line in out.splitlines() if needle in line]


# ---- stages ---------------------------------------------------------------------------------------------------------
def stage_plugins():
    header("0. Activate SqlConnector (COmanage CO > Configuration > Platform-Wide Configuration > Plugins)")
    ui("plugins")


def stage_file():
    header("1. File Provisioner")
    need(live_targets() == "0", "Redcurrant has no provisioning targets yet")
    ruth = person_id_by_login("ruth.spence")
    need(ruth, "Ruth Spence (ruth.spence) exists")
    with open(OUTPUT_HOST, "r+", encoding="utf-8") as f:
        f.truncate(0)
    print(f"  emptied provisioned/output.jsonl; Ruth Spence is person {ruth}")
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 5))
    ui("file-setup", ruth)
    errors = registry_log_since(since, "file_put_contents(): Argument #1 ($filename) must be of type string, null")
    record("1b The 500s are a TypeError in the File Provisioner", len(errors) >= 2,
           f"{len(errors)} registry log lines like: {errors[0][:220] if errors else '(none)'}")
    n = len(output_lines())
    record("1c Saving a target as Immediate provisions nobody by itself", n == 0,
           f"output.jsonl has {n} lines after setup and the trap tests")

    role = None
    temp = None
    events = [("role-add", "add a role to Ruth (Faculty, Associate Professor, Biology)"),
              ("role-title", "change the role title to Professor"),
              ("role-expire", "set the role to Expired (Ruth becomes Expired, i.e. ineligible)"),
              ("role-activate", "set the role back to Active"),
              ("provision-now", "Provision Now (File Export) on Ruth's Provisioning Status page"),
              ("temp-create", "add a person 'Temporary Person'"),
              ("temp-delete", "delete Temporary Person")]
    written = {}
    for name, what in events:
        before = output_lines()
        args = {"role-add": [ruth], "role-title": [role], "role-expire": [role], "role-activate": [role],
                "provision-now": [ruth, "File Export"], "temp-create": [], "temp-delete": [temp]}[name]
        got = ui("act", name, *args)
        role = got.get("ROLE_ID", role)
        temp = got.get("TEMP_ID", temp)
        new = output_lines()[len(before):]
        written[name] = new
        print(f"  {what}: {len(new)} line(s): {kinds(new)}")
    record("1c Immediate: an edit appends JSON lines at once",
           len(written["role-add"]) >= 1 and len(written["role-title"]) >= 1,
           f"role add wrote {len(written['role-add'])}, title change {len(written['role-title'])}, expiry "
           f"{len(written['role-expire'])}, reactivation {len(written['role-activate'])}, new person "
           f"{len(written['temp-create'])}, deletion {len(written['temp-delete'])} line(s)")
    expired = [json.loads(x) for x in written["role-expire"]]
    record("1c Ineligible subject writes only {\"id\":N}", bool(expired) and all(list(d) == ["id"] for d in expired),
           f"expiring Ruth's only role wrote {kinds(written['role-expire'])}")
    deleted = written["temp-delete"]
    record("1c Deleted subject writes only {\"id\":N}", bool(deleted) and list(json.loads(deleted[-1])) == ["id"],
           f"deleting Temporary Person wrote {kinds(deleted)}")
    record("1c Provision Now works synchronously", len(written["provision-now"]) == 1,
           f"one line appended before the page came back: {kinds(written['provision-now'])}")
    sample = next((x for x in written["role-title"] if "primary_name" in x), None)
    if sample:
        print("  sample line (trimmed):", trimmed(sample))

    header("1d. Reprovision All (File Export)")
    before = len(output_lines())
    ui("reprovision", "File Export")
    jobs = queued_provisioner_jobs()
    mid = len(output_lines())
    record("1d Reprovision All only queues jobs (People and Groups)",
           len(jobs) == 2 and mid == before and {"People", "Groups"} == {json.loads(j[1])["model"] for j in jobs},
           f"queued {[j[2] for j in jobs]}; output.jsonl unchanged ({before} -> {mid} lines) until the queue runs")
    run_jobs()
    summaries = job_summaries(jobs)
    new = output_lines()[mid:]
    people_lines = [k for k in kinds(new) if k.startswith("person")]
    people = rsql(f"select count(*) from people where co_id = {CO} and person_id is null and deleted is not true")
    record("1d People job writes one line per person", len(people_lines) == int(people),
           f"{len(new)} new lines ({len(people_lines)} people; Redcurrant has {people}); People job "
           f"'{summaries.get('People')}'")
    groups = rsql(f"select count(*) from groups where co_id = {CO} and group_id is null and deleted is not true")
    group3 = rsql(f"select name || ' in CO ' || co_id from groups where id = {CO}")
    record("1d Groups job is buggy (GroupsTable::getMembers called with the CO id)",
           "Reprovisioned 0 entities" in summaries.get("Groups", ""),
           f"Groups job '{summaries.get('Groups')}' although Redcurrant has {groups} groups; it iterates the members "
           f"of group id {CO} ({group3}), not the CO's groups")
    print(f"  output.jsonl now has {len(output_lines())} lines")


def target_counts():
    tables = ["sp_people", "sp_names", "sp_identifiers", "sp_person_roles", "sp_email_addresses", "sp_group_members",
              "sp_groups", "sp_cous", "sp_types"]
    q = " union all ".join(f"select '{t}', count(*) from {t}" for t in tables)
    return dict(r.split("|") for r in tsql(q).splitlines())


SAMPLE_QUERY = ("select p.id, p.status, n.given, n.family, i.identifier as login, r.title "
                "from sp_people p "
                "join sp_names n on n.person_id = p.id and n.primary_name "
                "left join sp_identifiers i on i.person_id = p.id and i.login "
                "left join sp_person_roles r on r.person_id = p.id "
                "order by n.family, n.given limit 5")


def stage_sql():
    header("2. SQL Provisioner")
    need(rsql("select status from plugins where plugin = 'SqlConnector'") == "A",
         "SqlConnector is active (stage plugins)")
    need(rsql(f"select count(*) from provisioning_targets where co_id = {CO} and provisioning_target_id is null and "
              f"deleted is not true and plugin = 'SqlConnector.SqlProvisioners'") == "0", "no SQL target yet")
    ruth = person_id_by_login("ruth.spence")
    old = tsql("select tablename from pg_tables where schemaname = 'public' and tablename like 'sp\\_%'").split()
    if old:
        tsql("drop table if exists " + ", ".join(old) + " cascade")
        print(f"  dropped {len(old)} sp_ tables left from an earlier run")
    found = ui("sql-setup")
    target = found["SQL_TARGET_ID"]
    tables = tsql("select tablename from pg_tables where schemaname = 'public' order by 1").split()
    counts = target_counts()
    record("2b Saving the SQL Provisioner creates the tables and syncs reference data",
           len(tables) > 0 and int(counts["sp_types"]) > 0 and int(counts["sp_people"]) == 0,
           f"{len(tables)} tables: {' '.join(tables)}; sp_types {counts['sp_types']}, sp_cous {counts['sp_cous']}, "
           f"sp_groups {counts['sp_groups']}, sp_people {counts['sp_people']}")
    print(tsql("\\dt", pretty=True))
    ui("sql-links", target)
    after = target_counts()
    record("2c Reapply/Resync leave the data as it was", after == counts,
           f"row counts before {counts} after {after}")
    ui("sql-immediate", target, ruth)
    c = target_counts()
    record("2d Provision Now writes one person to the sp_ tables",
           c["sp_people"] == "1" and int(c["sp_names"]) >= 1 and int(c["sp_identifiers"]) >= 1,
           f"sp_people {c['sp_people']}, sp_names {c['sp_names']}, sp_identifiers {c['sp_identifiers']}, "
           f"sp_person_roles {c['sp_person_roles']}, sp_group_members {c['sp_group_members']}, "
           f"sp_email_addresses {c['sp_email_addresses']}")

    header("2d. Reprovision All (SQL Export)")
    file_before = len(output_lines())
    ui("reprovision", "SQL Export")
    jobs = queued_provisioner_jobs()
    c_mid = target_counts()
    record("2d Reprovision All only queues jobs", len(jobs) == 2 and c_mid["sp_people"] == "1",
           f"queued {[j[2] for j in jobs]}; sp_people still {c_mid['sp_people']}")
    run_jobs()
    summaries = job_summaries(jobs)
    c = target_counts()
    expected = rsql(f"select count(*) from people where co_id = {CO} and person_id is null and deleted is not true")
    record("2d After the job run every person is in sp_people", c["sp_people"] == expected,
           f"sp_people {c['sp_people']} (Redcurrant has {expected} people), sp_names {c['sp_names']}, "
           f"sp_identifiers {c['sp_identifiers']}, sp_group_members {c['sp_group_members']}; jobs {summaries}; "
           f"the File Export got {len(output_lines()) - file_before} new lines (its queue is separate)")
    print("  sample query for participants:\n  " + SAMPLE_QUERY)
    print(tsql(SAMPLE_QUERY, pretty=True))


def stage_invite():
    header("3. Enrollment by invitation")
    need(rsql(f"select count(*) from enrollment_flows where co_id = {CO} and enrollment_flow_id is null and "
              f"deleted is not true and name = 'Invite a Member'") == "0", "no 'Invite a Member' flow yet")
    file_before = len(output_lines())
    found = ui("invite")
    casey = found["CASEY_ID"]
    ident = rsql(f"select i.identifier || ' / ' || t.display_name || ' / login=' || coalesce(i.login::text, '') "
                 f"from identifiers i join types t on t.id = i.type_id where i.person_id = {casey} and "
                 f"i.identifier_id is null and i.deleted is not true")
    record("3f New Person has the login identifier from the username", "casey.invitee / Network / login=true" in ident,
           f"person {casey}: {ident.splitlines()}")
    hijack = found["HIJACK_PETITION"]
    row = rsql(f"select status || ' / enrollee_identifier=' || coalesce(enrollee_identifier, '') || ' / token=' || "
               f"coalesce(token, '(none)') from petitions where id = {hijack}")
    record("3h Opening the link while logged in binds the invitation to that user", "enrollee_identifier=admin" in row,
           f"petition {hijack} after admin opened the link (then terminated): {row}")
    petitions = rsql(f"select id || ' ' || status || ' ' || coalesce(enrollee_email, '') || ' ' || "
                     f"coalesce(enrollee_identifier, '-') from petitions where petition_id is null and "
                     f"enrollment_flow_id = {found['FLOW_ID']} order by id").splitlines()
    print("  petitions (id status email identifier):", petitions)
    new = output_lines()[file_before:]
    casey_lines = [k for k in kinds(new) if k.startswith(f"person {casey} ")]
    sp = tsql(f"select p.id || ' ' || p.status || ' ' || n.given || ' ' || n.family from sp_people p join sp_names n "
              f"on n.person_id = p.id and n.primary_name where p.id = {casey}")
    sp_ident = tsql(f"select identifier from sp_identifiers where person_id = {casey} and login")
    record("3g The enrolled person is provisioned (File and SQL, Immediate)", bool(casey_lines) and bool(sp),
           f"output.jsonl: {casey_lines}; sp_people: '{sp}', login identifier in sp_identifiers: '{sp_ident}'")


def summary():
    header("Summary")
    for claim, verdict, evidence in RESULTS:
        print(f"  {verdict:<10} {claim}")
    bad = [c for c, v, _ in RESULTS if v == "REFUTED"]
    print(f"\n  {len(RESULTS)} checks, {len(bad)} refuted" + (f": {bad}" if bad else ""))
    print("  screenshots: tools/seed/out/t-*.png")


STAGES = {"plugins": stage_plugins, "file": stage_file, "sql": stage_sql, "invite": stage_invite}


def host_main(argv):
    if not argv or argv[0] not in list(STAGES) + ["all"]:
        sys.exit(__doc__)
    if "--restore" in argv:
        subprocess.run(["./workshop", "restore", "04-filesource-synced"], cwd=REPO, check=True)
    for old in (HERE / "out").glob("t-*.png"):
        if argv[0] == "all" or old.name.startswith(f"t-{argv[0]}-"):
            old.unlink()
    for stage in (list(STAGES) if argv[0] == "all" else [argv[0]]):
        STAGES[stage]()
    summary()


# =====================================================================================================================
# Browser side (in the Playwright container)
# =====================================================================================================================
MAILPIT = "http://mailpit:8025/api/v1"
INVITE_TEMPLATE = ("Redcurrant Invitation", "EH", "You are invited to join (@CO_NAME)", """Hello (@ENROLLEE_NAME),

You have been invited to join (@CO_NAME).

To accept the invitation, open this link:

(@ENTRY_URL)

You will be asked to log in. Use the username you want to keep for (@CO_NAME).

This message was sent to (@ENROLLEE_EMAIL).""")
WELCOME_TEMPLATE = ("Redcurrant Welcome", "EF", "Welcome to (@CO_NAME)", """Hello (@ENROLLEE_NAME),

Your enrollment in (@CO_NAME) is complete.

Log in to the Registry with the same username you used to accept the invitation.""")
FLOW = "Invite a Member"
WELCOME_MESSAGE = "Welcome to Redcurrant University. Please accept your invitation to continue."


OPEN = []  # every browser opened by a part, for screenshots on failure


def browser(pw, user, prefix, login=True):
    """A separate browser (like a private window) for one persona. Basic credentials go out only when the Registry
    asks for a login, so with login=False the window stays anonymous until then."""
    from registry import Registry
    r = Registry(pw, user=user, prefix=prefix)
    OPEN.append(r)
    if login:
        r.login()
    return r


def path_of(url):
    s = urlsplit(url)
    return s.path + (f"?{s.query}" if s.query else "")


def track(r):
    """Record the status and path of every page (document) response."""
    log = []
    r.page.on("response", lambda x: log.append((x.status, path_of(x.url)))
              if x.request.resource_type == "document" else None)
    return log


def visit(r, url):
    """Open a page that may fail (error page, redirect loop); return (error, title, text)."""
    if not url.startswith("http"):
        from registry import BASE
        url = f"{BASE}/{url}"
    try:
        r.page.goto(url)
        r.page.wait_for_load_state("networkidle")
    except Exception as e:  # e.g. net::ERR_TOO_MANY_REDIRECTS
        error = str(e).splitlines()[0]
        for _ in range(3):  # let the browser settle on its error page before the next navigation
            r.page.wait_for_timeout(1000)
            try:
                r.page.goto("about:blank")
                break
            except Exception:
                pass
        return error, "", ""
    return None, r.page.title(), r.page.locator("body").inner_text()


def menu(r, panel, item):
    """Open a left-navigation panel and click one of its links, as a participant does."""
    r.page.locator(f'#main-menu a.menu-panel-toggle[title="{panel}"]').first.click()
    r.page.wait_for_timeout(300)
    links = r.page.locator("#main-menu a:visible")
    names = links.evaluate_all("""els => els.map(a => { const c = a.cloneNode(true);
        c.querySelectorAll('[aria-hidden=true], .menu-panel-link-desc, .material-symbols, .material-symbols-outlined')
         .forEach(e => e.remove());
        return c.innerText.trim(); })""")  # the link's title only, without its icon name and description
    links.nth(names.index(item)).click()
    r.page.wait_for_load_state("networkidle")
    r.assert_ok(f"{panel} > {item}")


def click_text(r, text, scope="main"):
    r.page.locator(f"{scope} a:visible, {scope} button:visible", has_text=text).first.click()
    r.page.wait_for_load_state("networkidle")
    r.assert_ok(text)


def labels(r):
    return [f["label"] or f["name"] for f in r.describe_form() if f["visible"]]


def field(r, name):
    return next(f for f in r.describe_form() if f["name"] == name)


def option_text(r, name):
    return r.page.locator(f'form select[name="{name}"] option:checked').inner_text().strip()


def flash(r):
    return " | ".join(f.replace("check_circle", "").replace("report_problem", "").replace("info\n", "").strip()
                      for f in r.flashes())


def row_menu(r, row_text, scope="main table tr"):
    """Open the gear menu on a table row; return (row locator, item labels)."""
    row = r.page.locator(scope, has_text=row_text).first
    row.locator(".action-menu-toggle").first.click()
    r.page.wait_for_timeout(300)
    return row, menu_texts(row.locator(".dropdown-menu a"))


def menu_texts(links):
    """Visible labels of menu links, without their icon names."""
    return links.evaluate_all("""els => els.map(a => { const c = a.cloneNode(true);
        c.querySelectorAll('em, .material-symbols, .material-icons').forEach(e => e.remove());
        return c.innerText.trim().replace(/\\s+/g, ' '); }).filter(t => t)""")


def confirm(r, button):
    dlg = r.page.locator(".modal:visible").first
    dlg.wait_for()
    text = " | ".join(x.strip() for x in dlg.inner_text().splitlines() if x.strip())
    dlg.get_by_role("button", name=button, exact=True).click()
    r.page.wait_for_load_state("networkidle")
    return text


def save_person(r, person):
    """Open a person and press Save; return the HTTP status of the POST (302 = saved, 500 = error page)."""
    r.go(f"people/edit/{person}")
    log = track(r)
    r.page.get_by_role("button", name="Save", exact=True).first.click()
    r.page.wait_for_load_state("networkidle")
    status = log[0][0] if log else None
    body = r.page.locator("body").inner_text()
    return status, ("An Internal Error Has Occurred" in body), flash(r)


def set_target_mode(r, target, mode):
    r.go(f"provisioning-targets/edit/{target}")
    r.set("status", mode)
    r.save(f"target {target} mode {mode}")


def target_id_on_plugin_page(r):
    href = r.page.locator("main a", has_text="PROPERTIES").first.get_attribute("href")
    return int(re.search(r"/provisioning-targets/edit/(\d+)", href).group(1))


# ---- 0 ---------------------------------------------------------------------------------------------------------------
def ui_plugins(pw):
    r = browser(pw, "admin", "t-plugins-")
    r.go("dashboards/dashboard?co_id=1")
    menu(r, "Configuration", "Plugins")
    row, items = row_menu(r, "SqlConnector")
    status = r.page.locator("main table tr", has_text="SqlConnector").first.inner_text().split()
    if "Active" in status[1:]:
        record("0 Activate SqlConnector", "NOT TESTED", "already active; start from checkpoint 04")
        return
    r.shot("plugins-gear")
    row.locator(".dropdown-menu a", has_text="Activate").first.click()
    r.page.wait_for_load_state("networkidle")
    now = " ".join(r.page.locator("main table tr", has_text="SqlConnector").first.inner_text().split())
    record("0 Activate SqlConnector on the Plugins page", "Plugin Activated" in flash(r) and "Active" in now,
           f"COmanage CO > Configuration > Platform-Wide Configuration > Plugins ({r.page.url}); row gear menu "
           f"{items} > Activate; flash '{flash(r)}'; row now '{now}'")
    r.shot("plugins-activated")


# ---- 1 ---------------------------------------------------------------------------------------------------------------
def ui_file_setup(pw, ruth):
    r = browser(pw, "admin", "t-file-")
    r.go(f"dashboards/dashboard?co_id={CO}")
    menu(r, "Connections", "Provisioning Targets")
    click_text(r, "Add a New Provisioning Target")
    r.shot("target-add")
    plugins = [o[1] for o in field(r, "plugin")["options"] if o[0]]
    record("1a Add form: fields and defaults",
           option_text(r, "status") == "Queue on Error" and field(r, "retry_interval")["value"] == "900",
           f"fields {labels(r)}; Provisioning Mode options {[o[1] for o in field(r, 'status')['options']]}, "
           f"default '{option_text(r, 'status')}'; Retry Interval default {field(r, 'retry_interval')['value']}; "
           f"Max Retries default '{field(r, 'max_retry')['value']}'; Plugin options {plugins}")
    # A throwaway target, left in the default mode, whose plugin is never configured
    r.fill({"description": "Throwaway File Target", "plugin": "FileConnector.FileProvisioners"})
    r.save("add throwaway target")
    throwaway = target_id_on_plugin_page(r)
    heading = r.page.locator("main h2").first.inner_text().strip() if r.page.locator("main h2").count() else ""
    record("1a After Save: the plugin form with one field, File Name",
           "file-provisioners/edit/" in r.page.url and labels(r) == ["File Name"],
           f"landed on {path_of(r.page.url)} ('{heading}'), flash '{flash(r)}', fields {labels(r)}")
    r.set("filename", "/srv/provisioned/missing/output.jsonl")
    r.save("bad file name", expect_error=True)
    errors = " ".join(r.form_errors())
    record("1a A path that does not exist is refused: 'The file \"X\" is not writable'",
           'is not writable' in errors, f"'{errors}'")
    r.shot("not-writable")
    # 1b: the plugin form is abandoned; every person save in the CO now fails
    trap = []
    for mode, label in (("QE", "Queue on Error"), ("A", "Immediate")):
        set_target_mode(r, throwaway, mode)
        status, error_page, msg = save_person(r, ruth)
        trap.append(f"{label}: HTTP {status}{' error page' if error_page else ''} (flash '{msg}')")
        if mode == "QE":
            r.shot("trap-500")
    record("1b Unconfigured target + Queue on Error/Immediate: every person edit gives HTTP 500",
           all("HTTP 500" in t for t in trap), "; ".join(trap) +
           " (the error page also shows the 'Saved' flash: the Person is saved, then provisioning fails)")
    set_target_mode(r, throwaway, "X")
    status, error_page, msg = save_person(r, ruth)
    record("1b ... but not while the target is Disabled", status == 302 and not error_page,
           f"Disabled: HTTP {status}, flash '{msg}'")
    r.go(f"provisioning-targets/edit/{throwaway}")
    click_text(r, "Delete")
    dialog = confirm(r, "Delete")
    deleted = flash(r)
    status, error_page, msg = save_person(r, ruth)
    record("1b Deleting the throwaway target ends the 500s", "deleted" in deleted and status == 302,
           f"target's PROPERTIES page > Delete > dialog '{dialog}' > flash '{deleted}'; saving Ruth again: HTTP "
           f"{status}, flash '{msg}'")
    # Safe sequence: Disabled, configure, then Immediate
    menu(r, "Connections", "Provisioning Targets")
    click_text(r, "Add a New Provisioning Target")
    r.fill({"description": "File Export", "status": "X", "plugin": "FileConnector.FileProvisioners"})
    r.save("add File Export")
    r.set("filename", OUTPUT)
    r.save("File Export file name")
    target = r.id_from_url()
    landed = path_of(r.page.url)
    set_target_mode(r, target, "A")
    r.go(f"provisioning-targets?co_id={CO}")
    row = " ".join(r.page.locator("main table tr", has_text="File Export").first.inner_text().split())
    record("1b Safe sequence: Disabled, File Name, then Immediate", "Immediate" in row,
           f"File Name {OUTPUT} saved (landed on {landed}); list row '{row}'")
    r.shot("file-export")
    var("FILE_TARGET_ID", target)


def ui_act(pw, name, *args):
    r = browser(pw, "admin", f"t-file-{name}-")
    if name == "role-add":
        r.go(f"person-roles/add?person_id={args[0]}")
        r.fill({"affiliation_type_id": {"label": "Faculty"}, "status": "A", "title": "Associate Professor",
                "department": "Biology"})
        r.save("add role")
        var("ROLE_ID", r.id_from_url())
    elif name in ("role-title", "role-expire", "role-activate"):
        r.go(f"person-roles/edit/{args[0]}")
        r.set(*{"role-title": ("title", "Professor"), "role-expire": ("status", "XP"),
                "role-activate": ("status", "A")}[name])
        r.save(name)
    elif name == "provision-now":
        person, target = args
        provision_now(r, person, target)
    elif name == "temp-create":
        from seed import add_person
        var("TEMP_ID", add_person(r, CO, "Temporary", "Person"))
    elif name == "temp-delete":
        r.go(f"people/edit/{args[0]}")
        r.page.locator(".action-menu-toggle:visible").first.click()
        r.page.wait_for_timeout(300)
        r.page.locator(".dropdown-menu.show a", has_text="Delete").first.click()
        confirm(r, "Delete")
    print(f"{name}: {flash(r)}")
    r.shot(name)


def provision_now(r, person, target):
    r.go(f"people/edit/{person}")
    r.page.locator(".action-menu-toggle:visible").first.click()
    r.page.wait_for_timeout(300)
    gear = menu_texts(r.page.locator(".dropdown-menu.show a"))
    r.page.locator(".dropdown-menu.show a", has_text="Provisioning Status").first.click()
    r.page.wait_for_load_state("networkidle")
    head = " | ".join(t.strip() for t in r.page.locator("main table th").all_inner_texts() if t.strip())
    before = " ".join(r.page.locator("main table tr", has_text=target).first.inner_text().split())
    row, items = row_menu(r, target)
    row.locator(".dropdown-menu a", has_text="Provision Now").first.click()
    dialog = confirm(r, "Provision Now")
    after = " ".join(r.page.locator("main table tr", has_text=target).first.inner_text().split())
    print(f"person gear menu {gear}; Provisioning Status columns [{head}]; row before '{before}'; "
          f"row gear {items}; dialog '{dialog}'; flash '{flash(r)}'; row after '{after}'")
    r.shot(f"provision-now-{target}")
    return before, after


def ui_reprovision(pw, target):
    r = browser(pw, "admin", f"t-{target.split()[0].lower()}-reprovision-")
    r.go(f"dashboards/dashboard?co_id={CO}")
    menu(r, "Connections", "Provisioning Targets")
    row, items = row_menu(r, target)
    row.locator(".dropdown-menu a", has_text="Reprovision All").first.click()
    r.page.wait_for_load_state("networkidle")
    print(f"row gear menu {items}; Reprovision All (no confirmation) > flash '{flash(r)}'")
    r.shot("queued")
    menu(r, "Operations", "Jobs")
    print("Operations > Jobs:", " / ".join(" ".join(t.split()) for t in
                                           r.page.locator("main tr", has_text="ProvisionerJob").all_inner_texts()[:2]))
    r.shot("jobs")


# ---- 2 ---------------------------------------------------------------------------------------------------------------
def ui_sql_setup(pw):
    r = browser(pw, "admin", "t-sql-")
    r.go(f"dashboards/dashboard?co_id={CO}")
    menu(r, "Connections", "Servers")
    click_text(r, "Add a New Server")
    add_fields = labels(r)
    r.fill({"description": "Target Database", "status": "A", "plugin": "CoreServer.SqlServers"})
    r.save("add server")
    rdbms = [o[1] for o in field(r, "type")["options"] if o[0]]
    form = labels(r)
    landed = path_of(r.page.url)
    r.shot("sql-server-form")
    r.fill({"type": "PG", "hostname": "target-database", "port": "", "databas": "target", "username": "target_user",
            "password": "password"})
    r.save("SQL server")
    record("2a Servers > Add (Description, Status, Plugin) > SQL Server form",
           "core-server/sql-servers/edit/" in landed and "Postgres" in rdbms,
           f"Connections > Related Configurations > Servers > Add a New Server: fields {add_fields} (Plugin "
           f"CoreServer.SqlServers) > Save > {landed}: fields {form}, RDBMS Type options {rdbms}; values Postgres, "
           f"target-database, Port blank, target, target_user, password > Save > {path_of(r.page.url)} "
           f"flash '{flash(r)}'")
    menu(r, "Connections", "Provisioning Targets")
    click_text(r, "Add a New Provisioning Target")
    r.fill({"description": "SQL Export", "status": "X", "plugin": "SqlConnector.SqlProvisioners"})
    r.save("add SQL Export")
    servers = [o[1] for o in field(r, "server_id")["options"] if o[0]]
    prefix = field(r, "table_prefix")["value"]
    links = [t for t in ("Reapply Target Database Schema", "Resync Reference Data")
             if r.page.locator("main a:visible", has_text=t).count()]
    r.shot("sql-provisioner-form")
    record("2b SQL Provisioner form: Server (by Description), Table Name Prefix sp_",
           "Target Database" in servers and prefix == "sp_",
           f"landed on {path_of(r.page.url)}: fields {labels(r)}, Server options {servers}, prefix default "
           f"'{prefix}'; links already shown: {links}")
    r.fill({"server_id": {"label": "Target Database"}, "table_prefix": "sp_"})
    r.save("SQL provisioner")
    print(f"saved: {path_of(r.page.url)} flash '{flash(r)}'")
    var("SQL_TARGET_ID", r.id_from_url())


def ui_sql_links(pw, target):
    r = browser(pw, "admin", "t-sql-links-")
    r.go(f"provisioning-targets/edit/{target}")
    click_text(r, "CONFIGURE PLUGIN")
    where = path_of(r.page.url)
    out = []
    for link in ("Reapply Target Database Schema", "Resync Reference Data"):
        r.go(f"provisioning-targets/configure/{target}")
        click_text(r, link)
        out.append(f"'{link}' > flash '{flash(r)}', back on {path_of(r.page.url)}")
        r.shot(link.split()[0].lower())
    record("2c Links on the CONFIGURE PLUGIN tab: Reapply Target Database Schema, Resync Reference Data",
           "Schema Reapplied" in out[0] and "Reference Data Synced" in out[1], f"tab {where}: " + "; ".join(out))


def ui_sql_immediate(pw, target, ruth):
    r = browser(pw, "admin", "t-sql-immediate-")
    set_target_mode(r, target, "A")
    before, after = provision_now(r, ruth, "SQL Export")
    record("2d Provision Now (SQL Export) shows Provisioned", "Provisioned" in after,
           f"Provisioning Status row before '{before}', after '{after}'")


# ---- 3 ---------------------------------------------------------------------------------------------------------------
def mailpit(path):
    import urllib.request
    with urllib.request.urlopen(f"{MAILPIT}/{path}") as resp:
        return json.load(resp)


def mail_ids():
    return {m["ID"] for m in mailpit("messages?limit=200")["messages"]}


def wait_mail(to, seen, subject_part="", timeout=30):
    for _ in range(timeout):
        for m in mailpit("messages?limit=50")["messages"]:
            if m["ID"] not in seen and subject_part in m["Subject"] and any(t["Address"] == to for t in m["To"]):
                return mailpit(f"message/{m['ID']}")
        time.sleep(1)
    return None


def add_template(r, t):
    description, context, subject, body = t
    r.go(f"message-templates/add?co_id={CO}")
    r.fill({"description": description, "status": "A", "context": context, "format": "text",
            "subject": subject, "body_text": body})
    r.save(f"template {description}")


def modal(r, url_part, timeout=20):
    """The dialog the Registry opened for a cm-modal-link (an iframe), wrapped so the Registry helpers work in it."""
    from registry import RegistryError
    for _ in range(timeout * 5):
        for frame in r.page.frames:
            if url_part in frame.url:
                frame.wait_for_load_state("networkidle")
                inner = copy.copy(r)
                inner.page = frame
                return inner
        r.page.wait_for_timeout(200)
    raise RegistryError(f"no dialog showing {url_part}")


def close_modal(r):
    r.page.locator(".modal:visible .btn-close, .modal:visible [aria-label=Close]").first.click()
    r.page.wait_for_timeout(1000)
    r.page.wait_for_load_state("networkidle")


def add_step(r, flow, order, description, plugin, actor, config, extra=None):
    """Enrollment Flow Steps tab > Add a New Enrollment Flow Step: the form opens in a dialog; Save there shows the
    plugin's configuration in the same dialog; Save again, then close the dialog."""
    r.go(f"enrollment-flow-steps?enrollment_flow_id={flow}")
    r.page.locator("main a:visible", has_text="Add a New Enrollment Flow Step").first.click()
    m = modal(r, "enrollment-flow-steps/add")
    title = r.page.locator(".modal:visible .modal-title").first.inner_text().strip()
    step_form = labels(m)
    m.fill({"description": description, "status": "A", "plugin": plugin, "ordr": str(order), "actor_type": actor})
    if extra:
        m.fill(extra)
    m.save(f"step {description}")
    m.page.wait_for_url(lambda u: "/edit/" in u, timeout=20000)  # the dialog moves on to the plugin's form
    m.page.wait_for_load_state("networkidle")
    info = {"dialog": title, "step_form": step_form, "config_page": path_of(m.page.url),
            "config_heading": " / ".join(t.strip() for t in m.page.locator("h1, h2").all_inner_texts()),
            "config_form": labels(m),
            "defaults": {f["name"]: f["value"] for f in m.describe_form() if f["visible"]},
            "config_text": " ".join(m.page.locator("body").inner_text().split())}
    r.shot(f"step{order}-config")
    m.fill(config)
    m.save(f"configure {description}")
    m.page.wait_for_url(lambda u: "enrollment-flow-steps/edit/" in u, timeout=20000)
    m.page.wait_for_load_state("networkidle")
    info["after_config"] = path_of(m.page.url)
    close_modal(r)
    return info


def send_invitation(r, flow, given, family, email, via_menu=False):
    """As the CO administrator: Start the flow, give the enrollee's email, fill step 1. Returns details."""
    seen = mail_ids()
    info = {}
    if via_menu:
        r.go(f"dashboards/dashboard?co_id={CO}")
        menu(r, "People", "Enrollment Flows")
        row, info["row_menu"] = row_menu(r, FLOW)
        row.locator(".dropdown-menu a", has_text="Start").first.click()
        r.page.wait_for_load_state("networkidle")
    else:
        r.go(f"enrollment-flows/start/{flow}")
    r.assert_ok("start")
    info["start_fields"] = labels(r)
    r.set("enrollee_email", email)
    r.save("enrollee email")
    info["step1_heading"] = " / ".join(t.strip() for t in r.page.locator("main h1, main h2").all_inner_texts())
    info["step1_fields"] = labels(r)
    if via_menu:
        r.shot("step1")
    r.fill({"given": given, "family": family, "mail": email})
    r.page.get_by_role("button", name="Continue", exact=True).click()
    r.page.wait_for_load_state("networkidle")
    r.assert_ok("step 1")
    info["handoff_url"] = path_of(r.page.url)
    info["handoff_text"] = " ".join(r.page.locator("main").first.inner_text().split())
    if via_menu:
        r.shot("handoff")
    msg = wait_mail(email, seen, "invited")
    info["mail"] = msg
    info["link"] = re.search(r"https?://\S+/petitions/continue/\d+\?token=\w+", msg["Text"]).group(0) if msg else None
    info["petition"] = int(re.search(r"/continue/(\d+)", info["link"]).group(1)) if info["link"] else None
    info["sent"] = time.time()
    return info


def answer_invitation(r, link, accept=True):
    """Open the invitation link in this context and Accept or Decline. Returns (accept page text, log, result)."""
    log = track(r)
    err, title, body = visit(r, link)
    if err:
        return None, log, err
    page = " ".join(r.page.locator("main").first.inner_text().split())
    r.page.locator(f"label[for=accepted-{1 if accept else 0}]").click()
    r.page.get_by_role("button", name="Continue", exact=True).click()
    r.page.wait_for_load_state("networkidle")
    result = f"{path_of(r.page.url)} '{r.page.title()}' flash '{flash(r)}': " + \
        " ".join(r.page.locator("main").first.inner_text().split())[:300]
    return page, log, result


def ui_invite(pw):
    a = browser(pw, "admin", "t-invite-admin-")
    # 3d Message Templates
    a.go(f"dashboards/dashboard?co_id={CO}")
    menu(a, "Configuration", "Message Templates")
    click_text(a, "Add a New Message Template")
    contexts = [o[1] for o in field(a, "context")["options"] if o[0]]
    formats = [o[1] for o in field(a, "format")["options"] if o[0]]
    add_template(a, INVITE_TEMPLATE)
    add_template(a, WELCOME_TEMPLATE)
    a.go(f"message-templates?co_id={CO}")
    listed = " / ".join(" ".join(t.split()) for t in a.page.locator("main table tr").all_inner_texts()[1:])
    record("3d Message Templates: contexts include Enrollment Handoff and Enrollment Finalization",
           "Enrollment Handoff" in contexts and "Enrollment Finalization" in contexts,
           f"Configuration > Personalization > Message Templates > Add; Context options {contexts}; Message Format "
           f"options {formats}; saved: {listed}")
    # 3a/3e the flow
    menu(a, "People", "Enrollment Flows")
    click_text(a, "Add a New Enrollment Flow")
    authz = [o[1] for o in field(a, "authz_type")["options"] if o[0]]
    collect_default = a.page.locator('form [name="collect_enrollee_email"]:not([type="hidden"])').is_checked()
    flow_fields = labels(a)
    record("3a Petitioner Authorization offers only Any Authenticated User and CO Administrator",
           authz == ["Any Authenticated User", "CO Administrator"], f"options {authz}")
    a.fill({"name": FLOW, "description": "An administrator invites someone by email", "status": "A",
            "authz_type": "CA", "collect_enrollee_email": True,
            "finalization_message_template_id": {"label": WELCOME_TEMPLATE[0]}})
    a.save("flow")
    flow = a.id_from_url()
    var("FLOW_ID", flow)
    tabs = [" ".join(t.split()) for t in a.page.locator("main a", has_text="START").all_inner_texts()]
    a.go(f"enrollment-flow-steps/add?enrollment_flow_id={flow}")  # the options, read once outside the dialog
    actor_types = [o[1] for o in field(a, "actor_type")["options"] if o[0]]
    handoff_options = [o[1] for o in field(a, "message_template_id")["options"] if o[0]]
    s1 = add_step(a, flow, 1, "Enter invitee details", "CoreEnroller.BasicAttributeCollectors", "P",
                  {"name_type_id": {"label": "Official"}, "email_address_type_id": {"label": "Official"},
                   "affiliation_type_id": {"label": "Member"}})
    s2 = add_step(a, flow, 2, "Accept invitation", "CoreEnroller.InvitationAccepters", "E",
                  {"invitation_validity": "5", "welcome_message": WELCOME_MESSAGE},
                  {"message_template_id": {"label": INVITE_TEMPLATE[0]}})
    accepter = re.search(r"invitation-accepters/edit/(\d+)", s2["config_page"]).group(1)
    s3 = add_step(a, flow, 3, "Link your login", "CoreEnroller.IdentifierCollectors", "E",
                  {"type_id": {"label": "Network"}})
    a.go(f"enrollment-flow-steps?enrollment_flow_id={flow}")
    steps = " / ".join(" ".join(t.split()) for t in a.page.locator("main table tr").all_inner_texts()[1:])
    a.shot("flow-steps")
    record("3e Flow and steps as described",
           s1["config_form"][:3] == ["Name Type", "Email Address Type", "Affiliation Type"]
           and s2["config_form"] == ["Invitation Validity", "Welcome Message"] and s3["config_form"] == ["Type"]
           and s2["defaults"].get("invitation_validity") == "1440",
           f"flow fields {flow_fields} (Collect Enrollee Email ticked by default: {collect_default}); flow page links "
           f"{tabs}; 'Add a New Enrollment Flow Step' opens a dialog titled '{s1['dialog']}' with fields "
           f"{s1['step_form']}, Actor Type options {actor_types}, Handoff Message Template options {handoff_options}; "
           f"Save shows '{s1['config_heading']}' ({s1['config_page']}) in the dialog; step 1 config "
           f"{s1['config_form']}; step 2 config {s2['config_form']} defaults {s2['defaults']}; step 3 config "
           f"{s3['config_form']}; Save on the config returns the dialog to {s3['after_config']}; steps: {steps}")
    # 3b the platform admin cannot start a CO Administrator flow in a CO where it is not a Person
    log = track(a)
    err, title, body = visit(a, f"enrollment-flows/start/{flow}")
    hops = [p for _, p in log[:6]]
    record("3b admin (not a Person in Redcurrant) cannot start the CO Administrator flow",
           bool(err) and "TOO_MANY_REDIRECTS" in err,
           f"{err or title}; redirect cycle {' > '.join(hops)} ...")
    # 3c the CO administrator persona: Ruth Spence (login ruth.spence from the HR file) in CO:admins
    a.go(f"dashboards/dashboard?co_id={CO}")
    menu(a, "Structure", "Groups")
    a.page.locator("main table a", has_text="CO:admins").first.click()
    a.page.wait_for_load_state("networkidle")
    click_text(a, "GROUP MEMBERS")
    picker = a.page.locator('input[placeholder="enter name, email address, or identifier"]').first
    picker.click()
    picker.press_sequentially("Spence", delay=60)
    a.page.locator("[role=option]", has_text="Ruth Spence").first.click()
    dialog = modal(a, "group-members/add")
    dialog_title = a.page.locator(".modal:visible .modal-title").first.inner_text().strip()
    dialog_form = labels(dialog)
    dialog.page.get_by_role("button", name="Save", exact=True).click()
    dialog.page.wait_for_url(lambda u: "group-members/edit/" in u, timeout=20000)
    dialog.page.wait_for_load_state("networkidle")
    after_save = " / ".join(t.strip() for t in dialog.page.locator("h1, h2").all_inner_texts()[:1]) + \
        f" ({flash(dialog)})"
    close_modal(a)
    a.page.locator("main table", has_text="Ruth Spence").first.wait_for(timeout=20000)
    a.shot("ruth-in-admins")
    ruth = browser(pw, "ruth.spence", "t-invite-ruth-")
    landing = path_of(ruth.page.url)
    panels = " ".join(ruth.page.locator("#main-menu").first.inner_text().split()) \
        if ruth.page.locator("#main-menu").count() else "(no menu)"
    ruth.shot("landing")
    member = browser(pw, "rachel.payne", "t-invite-member-")
    member_menu = member.page.locator("#main-menu").count()
    record("3c ruth.spence in CO:admins gets Redcurrant's admin menus",
           "co_id=3" in landing and "Configuration" in panels and member_menu == 0,
           f"Structure > Groups > CO:admins > GROUP MEMBERS > 'Add member:' picker, type Spence, choose Ruth Spence > "
           f"dialog '{dialog_title}' (Add a New Group Member, fields {dialog_form}) > Save > the dialog shows "
           f"'{after_save}' > close it. ruth.spence lands on {landing} with menu [{panels}]; an "
           f"ordinary member (rachel.payne) lands on {path_of(member.page.url)} with no menu")
    member.close()
    # 3e invitation validity unit: 5 means 5 seconds
    exp = send_invitation(ruth, flow, "Riley", "Expiry", "riley.expiry@example.org")
    time.sleep(max(0, 15 - (time.time() - exp["sent"])))
    inv = browser(pw, "riley.expiry", "t-invite-expiry-", login=False)
    page, log, result = answer_invitation(inv, exp["link"])
    inv.shot("expired")
    inv.close()
    help_text = re.search(r"Invitation Validity \* Required (.*?) Welcome Message", s2["config_text"])
    record("3e Invitation Validity is in SECONDS (label says minutes)", "This Invitation has expired" in result,
           f"validity 5, accept page opened ~15 s after sending (< 5 minutes), Accept > Continue: {result[:170]}; "
           f"the form's help text says '{help_text.group(1) if help_text else s2['config_text'][:120]}'")
    a.go(f"core-enroller/invitation-accepters/edit/{accepter}")
    a.set("invitation_validity", "0")
    a.save("validity 0")
    # 3f the real run
    casey = send_invitation(ruth, flow, "Casey", "Invitee", "casey.invitee@example.org", via_menu=True)
    ruth.go(f"dashboards/dashboard?co_id={CO}")
    menu(ruth, "People", "Petitions")
    prow = " ".join(ruth.page.locator("main table tr", has_text=f"Petition {casey['petition']}").first
                    .inner_text().split())
    ruth.shot("petitions")
    m = casey["mail"]
    record("3f Start > Enrollee Email > step 1 > handoff page; petition Pending Acceptance; invitation mail",
           "Thank you for completing this Enrollment Flow Step" in casey["handoff_text"] and "Pending Acceptance" in prow
           and casey["link"] is not None,
           f"People > Enrollment Flows > row gear {casey['row_menu']} > Start: fields {casey['start_fields']} > Save > "
           f"'{casey['step1_heading']}' fields {casey['step1_fields']} > Continue > {casey['handoff_url']}: "
           f"'{casey['handoff_text']}'. Petitions row: '{prow}'. Mail from {m['From']['Address']} to "
           f"{[t['Address'] for t in m['To']]}, subject '{m['Subject']}', link {casey['link']}")
    print("invitation mail body:\n" + m["Text"].rstrip())
    record("3d Substitutions are filled in the delivered invitation",
           "(@" not in m["Text"] + m["Subject"] and "Hello Casey Invitee" in m["Text"] and casey["link"] in m["Text"],
           f"subject '{m['Subject']}'; body starts '{' '.join(m['Text'].split())[:150]}'; reply-to "
           f"{[x['Address'] for x in m.get('ReplyTo', [])]}")
    seen = mail_ids()
    inv = browser(pw, "casey.invitee", "t-invite-casey-", login=False)
    page, log, result = answer_invitation(inv, casey["link"])
    inv.shot("complete")
    hops = " > ".join(p.split("?")[0] for _, p in log)
    record("3f Accept page, Accept > Continue > login as the new username > Enrollment Complete",
           "Petition Finalized" in result and "auth/login" in hops,
           f"accept page: '{page}'. After Accept + Continue: {hops} => {result}")
    welcome = wait_mail("casey.invitee@example.org", seen, "Welcome")
    record("3f Welcome mail arrives", welcome is not None,
           f"subject '{welcome['Subject'] if welcome else None}': "
           f"{' '.join(welcome['Text'].split()) if welcome else ''}")
    again = browser(pw, "casey.invitee", "t-invite-casey-again-")
    landing = path_of(again.page.url)
    again.shot("landing")
    again.close()
    log = track(inv)
    err, title, body = visit(inv, casey["link"])
    reopen = err or f"HTTP {log[-1][0] if log else '?'} '{title}'"
    inv.close()
    from seed import find_id
    cid = find_id(a, f"people?co_id={CO}", "Casey Invitee", "people")
    var("CASEY_ID", cid)
    a.go(f"people/edit/{cid}")
    idents = " ".join(a.page.locator("main").first.inner_text().split("Identifiers", 1)[-1].split()[:12])
    a.shot("casey")
    record("3f casey.invitee logs in again and lands in Redcurrant", "co_id=3" in landing,
           f"landing {landing}; person {cid} identifiers: {idents}; reopening the used link afterwards: {reopen}")
    # 3h opening the link in a context that is already logged in (admin)
    jordan = send_invitation(ruth, flow, "Jordan", "Hijack", "jordan.hijack@example.org")
    var("HIJACK_PETITION", jordan["petition"])
    log = track(a)
    err, title, body = visit(a, jordan["link"])
    seen_by_admin = " ".join(body.split())[:200] if not err else err
    a.shot("hijack-admin")
    first = log[0][0] if log else None
    inv = browser(pw, "jordan.hijack", "t-invite-jordan-", login=False)
    log2 = track(inv)
    err2, _, _ = visit(inv, jordan["link"])
    inv.close()
    record("3h Opening the invitation while logged in (admin): 403 and the invitation is taken",
           first == 403 and bool(err2),
           f"admin gets HTTP {first}: '{seen_by_admin}'; the real invitee (fresh window, logs in as jordan.hijack) then "
           f"gets {err2 or 'a page'} via {' > '.join(p.split('?')[0] for _, p in log2[:5])}")
    ruth.go(f"petitions/view/{jordan['petition']}")
    click_text(ruth, "Terminate")
    dialog = confirm(ruth, "Terminate")
    record("3h Recovery: Petitions > View > Terminate, then send a new invitation", "Petition Terminated" in flash(ruth),
           f"dialog '{dialog}', flash '{flash(ruth)}'")
    # 3i Decline
    dana = send_invitation(ruth, flow, "Dana", "Decline", "dana.decline@example.org")
    seen = mail_ids()
    inv = browser(pw, "dana.decline", "t-invite-decline-", login=False)
    page, log, result = answer_invitation(inv, dana["link"], accept=False)
    inv.shot("declined")
    time.sleep(5)
    new_mail = [m["Subject"] + " > " + ",".join(t["Address"] for t in m["To"])
                for m in mailpit("messages?limit=50")["messages"] if m["ID"] not in seen]
    log = track(inv)
    err, title, body = visit(inv, dana["link"])
    reopen = err or f"HTTP {log[-1][0] if log else '?'} '{title}'"
    inv.close()
    record("3i Decline: what the invitee sees, and who is mailed", "Invitation Declined" in result,
           f"{result}; new mail after declining: {new_mail or 'none'}; reopening the link: {reopen}")
    ruth.close()
    a.close()


UI_PARTS = {"plugins": ui_plugins, "file-setup": ui_file_setup, "act": ui_act, "reprovision": ui_reprovision,
            "sql-setup": ui_sql_setup, "sql-links": ui_sql_links, "sql-immediate": ui_sql_immediate,
            "invite": ui_invite}


def ui_main(part, args):
    from registry import sync_playwright
    with sync_playwright() as pw:
        try:
            UI_PARTS[part](pw, *args)
        except Exception:
            for r in OPEN:  # show where each persona's window was when it failed
                try:
                    print(f"FAILED: {r.user} was on {r.page.url}")
                    r.shot("FAILED")
                except Exception:
                    pass
            raise


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ui":
        IN_UI = True
        ui_main(sys.argv[2], sys.argv[3:])
    else:
        host_main(sys.argv[1:])
