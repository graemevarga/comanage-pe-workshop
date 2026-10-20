"""End-to-end check of checkpoint 06: a brand-new username signs up through "Join Discovery TNG".
The verification code is read from Mailpit, like a participant reading their mail."""
import json
import re
import sys
import time
import urllib.request

from registry import BASE, Registry, RegistryError, sync_playwright

MAILPIT = "http://mailpit:8025/api/v1"
USER = sys.argv[1] if len(sys.argv) > 1 else "pat.newcomer"
EMAIL = f"{USER}@discovery-tng.example"


def mailpit(path):
    with urllib.request.urlopen(f"{MAILPIT}/{path}") as resp:
        return json.load(resp)


def wait_for_mail(subject_part, to):
    for _ in range(30):
        for m in mailpit("messages")["messages"]:
            if subject_part in m["Subject"] and any(t["Address"] == to for t in m["To"]):
                return mailpit(f"message/{m['ID']}")
        time.sleep(1)
    raise RegistryError(f"no mail '{subject_part}' to {to} in Mailpit")


with sync_playwright() as pw:
    r = Registry(pw, user=USER, prefix=f"v-enroll-{USER}-")
    flow = 1
    r.go(f"enrollment-flows/start/{flow}")
    r.shot("start")
    r.set("enrollee_email", EMAIL)
    r.save("enrollee email")
    r.shot("about-you")
    r.fill({"given": "Pat", "family": "Newcomer", "mail": EMAIL})
    r.page.get_by_role("button", name="Continue", exact=True).click()
    r.page.wait_for_load_state("networkidle")
    r.assert_ok("about you")
    r.shot("verify-page")
    r.click('a[href*="op=verify"]', "send verification code")
    msg = wait_for_mail("email verification code", EMAIL)
    code = re.search(r"[234679CDFGHJKLMNPQRTVWXZ]{4}-[234679CDFGHJKLMNPQRTVWXZ]{4}", msg["Text"]).group(0)
    print("verification mail:", msg["Subject"], "| code", code)
    r.set("code", code)
    r.page.get_by_role("button", name="Verify Email", exact=True).click()
    r.page.wait_for_load_state("networkidle")
    r.assert_ok("verify code")
    r.shot("verified")
    r.click("Finish", "finish")
    r.shot("complete")
    print("final page:", r.page.url, "|", r.page.title(), "|", r.flashes())
    welcome = wait_for_mail("Welcome to", EMAIL)
    print("welcome mail:", welcome["Subject"])
    r.close()
    # Log in again as the new person: Discovery TNG should now be one of their COs.
    r2 = Registry(pw, user=USER, prefix=f"v-enroll-{USER}-after-")
    r2.login()
    r2.go("cos/select")
    print("after enrollment, COs:", [a.inner_text().strip() for a in r2.page.locator("main table a").all()])
    r2.shot("cos")
    r2.close()
