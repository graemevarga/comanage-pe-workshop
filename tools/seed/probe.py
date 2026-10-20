"""Dump the real form fields of Registry pages (name, type, required, options, label) as JSON.
Usage: python probe.py PATH [PATH ...]   (paths relative to the webroot, e.g. "servers/add?co_id=1")"""
import json
import os
import re
import sys
from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "https://registry/registry-pe")
OUT = os.environ.get("OUT", "out")
USER = os.environ.get("REG_USER", "admin")

JS = r"""
() => {
  const out = [];
  for (const el of document.querySelectorAll('main form input, main form select, main form textarea, form input, form select, form textarea')) {
    if (!el.name || out.some(o => o.name === el.name && o.type === (el.type || el.tagName.toLowerCase()) && o.value === el.value && el.type !== 'radio')) continue;
    const lab = el.id ? document.querySelector(`label[for="${el.id}"]`) : null;
    const rec = {name: el.name, type: el.type || el.tagName.toLowerCase(), id: el.id || null,
                 required: !!el.required, label: lab ? lab.innerText.trim().slice(0, 80) : null,
                 visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)};
    if (el.tagName === 'SELECT') rec.options = [...el.options].map(o => [o.value, o.text.trim()]);
    if (el.type === 'hidden' || el.type === 'checkbox' || el.type === 'radio' || el.value) rec.value = el.value.slice(0, 120);
    out.push(rec);
  }
  const buttons = [...document.querySelectorAll('form button, form input[type=submit]')].map(b => (b.innerText || b.value || '').trim()).filter(Boolean);
  const flash = [...document.querySelectorAll('.alert, .flash, [role=alert], .message')].map(e => e.className + ': ' + e.innerText.trim().slice(0, 200));
  const title = (document.querySelector('h1') || {}).innerText || document.title;
  return {title, fields: out, buttons, flash};
}
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(ignore_https_errors=True, viewport={"width": 1440, "height": 1000},
                              http_credentials={"username": USER, "password": ""})
    page = ctx.new_page()
    page.goto(BASE + "/")
    page.click("#welcome-login-button")
    page.wait_for_load_state("networkidle")
    result = {}
    for path in sys.argv[1:]:
        page.goto(f"{BASE}/{path}")
        page.wait_for_load_state("networkidle")
        info = page.evaluate(JS)
        info["url"] = page.url
        result[path] = info
        page.screenshot(path=f"{OUT}/probe-{re.sub(r'[^A-Za-z0-9]+', '_', path)}.png", full_page=True)
    print(json.dumps(result, indent=1))
    browser.close()
