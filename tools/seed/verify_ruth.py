"""Rehearse the course's live sequence: Ruth Spence's Faculty/Staff role expires, a Retirees role is added."""
import re
from registry import Registry, sync_playwright
from seed import find_id, add_role
with sync_playwright() as pw:
    r = Registry(pw, prefix="v-ruth-")
    r.login()
    ruth = find_id(r, "people?co_id=3", "Ruth Spence", "people")
    r.go(f"person-roles?person_id={ruth}")
    href = [a.get_attribute("href") for a in r.page.locator("main table a").all() if "person-roles/edit" in (a.get_attribute("href") or "")][0]
    r.go(href)
    r.set("status", "XP")
    r.save("expire Faculty/Staff role")
    r.go(f"people/edit/{ruth}")
    print("after expiry:", r.page.locator("h1").first.inner_text(), "|", r.page.locator(".badge, .status-badge, [class*=badge]").all_inner_texts()[:3])
    r.shot("expired")
    add_role(r, ruth, {"cou_id": {"label": "Retirees"}, "affiliation_type_id": {"label": "Member"},
                       "status": "A", "title": "Associate Professor", "department": "Biology"})
    r.go(f"people/edit/{ruth}")
    print("after retirees role:", r.page.locator(".badge, .status-badge, [class*=badge]").all_inner_texts()[:3])
    r.shot("retiree")
    r.close()
