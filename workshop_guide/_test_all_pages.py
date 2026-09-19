"""Smoke test: every page renders without raising, and the completion mechanic works.

Run from the workshop_guide directory:
    .venv/bin/python _test_all_pages.py
"""
import importlib
import re
import sys

from streamlit.testing.v1 import AppTest

sys.path.insert(0, ".")

PAGES = [
    "app_pages/home.py",
    "app_pages/getting_started.py",
    "app_pages/agenda.py",
    "app_pages/session_01.py",
    "app_pages/session_02.py",
    "app_pages/session_03.py",
    "app_pages/session_04.py",
    "app_pages/session_05.py",
    "app_pages/session_06.py",
]

# These are filled in by the facilitator on the day and are expected to remain.
EXPECTED_PLACEHOLDERS = {
    "CI_ACCOUNT_IDENTIFIER", "CI_ROLE", "CI_WAREHOUSE", "CI_SANDBOX_DB", "CI_USERNAME",
}

failures = []

print(f"{'page':<34} {'exc':>4} {'cb':>3} {'code':>5} {'md':>4}  placeholders")
print("-" * 86)

for page in PAGES:
    at = AppTest.from_file(page, default_timeout=60)
    at.run()

    n_exc, n_cb = len(at.exception), len(at.checkbox)
    n_code, n_md = len(at.code), len(at.markdown)

    blobs = [m.value for m in at.markdown] + [c.value for c in at.code]
    blobs += [w.value for w in at.warning] + [i.value for i in at.info]
    found = set()
    for b in blobs:
        if isinstance(b, str):
            found.update(re.findall(r"\{\{(\w+)\}\}", b))
    unexpected = sorted(found - EXPECTED_PLACEHOLDERS)

    status = "-" if n_exc == 0 else str(n_exc)
    note = "OK" if not unexpected else "UNEXPECTED: " + ",".join(unexpected)
    print(f"{page:<34} {status:>4} {n_cb:>3} {n_code:>5} {n_md:>4}  {note}")

    if n_exc:
        for e in at.exception:
            failures.append(f"{page}: exception: {e.value}")
    if unexpected:
        failures.append(f"{page}: unexpected placeholders {unexpected}")
    if n_md < 3:
        failures.append(f"{page}: suspiciously little content ({n_md} markdown blocks)")

print()
print("completion mechanic:")
comp = importlib.import_module("components")
for n in range(1, 7):
    at = AppTest.from_file(f"app_pages/session_{n:02d}.py", default_timeout=60)
    at.run()
    expected = len(comp.SESSION_PROMPTS[n])
    actual = len(at.checkbox)
    for cb in at.checkbox:
        cb.check()
    at.run()
    done = at.session_state.get("_done", {})
    complete = all(done.get(comp._prompt_key(p), False) for p in comp.SESSION_PROMPTS[n])
    ok = (actual == expected) and complete
    print(f"  session {n}: {actual}/{expected} checkboxes, all-complete={complete} "
          f"{'OK' if ok else 'FAIL'}")
    if not ok:
        failures.append(
            f"session {n}: checkbox count {actual} vs {expected}, complete={complete}")

print()
if failures:
    print(f"FAILURES ({len(failures)}):")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("ALL PAGES PASS")
