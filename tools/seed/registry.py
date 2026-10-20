"""Small Playwright helper for driving the COmanage Registry PE 5.2.0 web UI (workshop seeding).

Forms are filled by HTML name attribute, so FormProtection's token stays valid (no fields are added or removed).
Select values may be given as the option value, or as {"label": "..."} to pick by visible text.
"""
import os
import re

from playwright.sync_api import sync_playwright  # noqa: F401  (re-exported for scripts)

BASE = os.environ.get("BASE", "https://registry/registry-pe")
OUT = os.environ.get("OUT", "out")


class RegistryError(RuntimeError):
    pass


class Registry:
    def __init__(self, pw, user="admin", prefix="", record_video=False):
        self.browser = pw.chromium.launch()
        self.ctx = self.browser.new_context(
            ignore_https_errors=True, viewport={"width": 1440, "height": 1000}, locale="en-US",
            timezone_id="UTC", http_credentials={"username": user, "password": ""})
        self.page = self.ctx.new_page()
        self.page.set_default_timeout(30000)
        self.user = user
        self.prefix = prefix
        self.shots = 0

    # ---- navigation ---------------------------------------------------------------------------------
    def login(self):
        """Log in the way a participant does: landing page -> Login button -> Basic auth (blank password)."""
        self.page.goto(f"{BASE}/")
        self.page.click("#welcome-login-button")
        self.page.wait_for_load_state("networkidle")
        self.assert_ok("login")
        return self.page.url

    def go(self, path, what=None):
        self.page.goto(f"{BASE}/{path.lstrip('/')}")
        self.page.wait_for_load_state("networkidle")
        self.assert_ok(what or path)
        return self.page.url

    def click(self, selector_or_text, what=None):
        loc = self._locator(selector_or_text)
        loc.click()
        self.page.wait_for_load_state("networkidle")
        self.assert_ok(what or str(selector_or_text))
        return self.page.url

    def _locator(self, s):
        if s.startswith(("text=", "role=", "#", ".", "a[", "button", "input", "[", "//", "css=")):
            return self.page.locator(s).first
        return self.page.get_by_role("link", name=s, exact=True).or_(
            self.page.get_by_role("button", name=s, exact=True)).first

    # ---- forms ----------------------------------------------------------------------------------------
    def field(self, name):
        loc = self.page.locator(f'form [name="{name}"]:not([type="hidden"])')
        if loc.count() == 0:
            raise RegistryError(f"no form field named {name!r} on {self.page.url}")
        return loc.first

    def set(self, name, value):
        loc = self.field(name)
        tag = loc.evaluate("e => e.tagName.toLowerCase()")
        typ = (loc.get_attribute("type") or "").lower()
        if tag == "select":
            if isinstance(value, dict) and "label" in value:
                loc.select_option(label=value["label"])
            else:
                loc.select_option(value=str(value))
            # Some forms show/hide fields from a change handler.
            self.page.wait_for_timeout(150)
        elif typ == "checkbox":
            loc.set_checked(bool(value))
        elif typ == "radio":
            self.page.locator(f'form [name="{name}"][value="{value}"]').check()
        else:
            loc.fill("" if value is None else str(value))

    def fill(self, fields):
        for name, value in fields.items():
            self.set(name, value)

    def save(self, what, button="Save", expect_error=False):
        """Submit the form and fail loudly on validation errors or error pages."""
        self.page.get_by_role("button", name=button, exact=True).first.click()
        self.page.wait_for_load_state("networkidle")
        errors = self.form_errors()
        if errors and not expect_error:
            self.shot(f"ERROR-{what}")
            raise RegistryError(f"{what}: form rejected: {errors}")
        self.assert_ok(what)
        return self.page.url

    def form_errors(self):
        sels = [".error-message", ".invalid-feedback", ".alert-danger", ".alert-error", ".co-alert.error",
                ".flash-error", ".message.error"]
        msgs = []
        for sel in sels:
            for e in self.page.locator(sel).all():
                if e.is_visible():
                    t = e.inner_text().strip()
                    if t:
                        msgs.append(t[:300])
        return msgs

    def flashes(self):
        return [e.inner_text().strip()[:300] for e in self.page.locator(
            ".alert, [role=alert], .co-alert, .flash, .message").all() if e.is_visible()]

    def assert_ok(self, what):
        title = self.page.title()
        h1 = self.page.locator("h1").first.inner_text().strip() if self.page.locator("h1").count() else ""
        if title.strip().lower() == "error" or h1.lower() in ("error", "an internal error has occurred"):
            self.shot(f"ERROR-{what}")
            body = self.page.locator("body").inner_text()[:800]
            raise RegistryError(f"{what}: error page at {self.page.url}: {body}")

    # ---- reading ----------------------------------------------------------------------------------------
    def describe_form(self):
        """Visible form fields on the current page: name, type, label, options (for exploring)."""
        return self.page.evaluate(r"""() => [...document.querySelectorAll('form input, form select, form textarea')]
          .filter(e => e.name && e.type !== 'hidden' && !['q', 'setting-dark-mode', 'setting-density'].includes(e.name))
          .map(e => { const l = e.id ? document.querySelector(`label[for="${e.id}"]`) : null;
                      return {name: e.name, type: e.type, required: e.required, value: e.value,
                              visible: !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length),
                              label: l ? l.innerText.trim().slice(0, 60) : null,
                              options: e.tagName === 'SELECT' ? [...e.options].map(o => [o.value, o.text.trim()]) : undefined}; })""")

    def id_from_url(self, url=None):
        m = re.search(r"/(?:edit|view)/(\d+)", url or self.page.url)
        return int(m.group(1)) if m else None

    def text(self):
        return self.page.locator("main").first.inner_text() if self.page.locator("main").count() else \
            self.page.locator("body").inner_text()

    # ---- evidence -----------------------------------------------------------------------------------------
    def shot(self, name):
        self.shots += 1
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        path = f"{OUT}/{self.prefix}{self.shots:02d}-{safe}.png"
        self.page.screenshot(path=path, full_page=True)
        return path

    def close(self):
        self.browser.close()
