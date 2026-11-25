"""Stage Falcon 14.2 Payhip Store Mode and automatic approved-site preview.

Build-time only. Does not install or launch software on the build machine.
The user will initiate /money payhip (or select the new command menu item)
from Falcon's existing chat; this opens official https://payhip.com/ and
prepares an unsold local product draft without a Payhip API/login.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/Falcon_Ai_V14_1_Candidate"
BASE_RUNTIME = ROOT / "build/falcon_app_v141_runtime"
TARGET = ROOT / "build/Falcon_Ai_V14_2_Candidate"
RUNTIME = ROOT / "build/falcon_app_v142_runtime"
PREVIOUS = "14.1.0"
VERSION = "14.2.0"

if (BASE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != PREVIOUS:
    raise RuntimeError("Verified Falcon V14.1 source is required")
if "CURRENT_VERSION = (14, 1, 0)" not in (BASE_RUNTIME / "app_updates.py").read_text():
    raise RuntimeError("Expected the verified V14.1 updater")
for directory in (TARGET, RUNTIME):
    if directory.exists():
        shutil.rmtree(directory)
shutil.copytree(BASE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copytree(BASE_RUNTIME, RUNTIME, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))

for module in ("payhip_store.py", "website_preview.py", "payhip_browser_agent.py"):
    shutil.copy2(ROOT / "packaging" / module, TARGET / module)


def replace(file, before, after):
    file = Path(file)
    body = file.read_text(encoding="utf-8")
    if body.count(before) != 1:
        raise RuntimeError("Ambiguous V14.2 source anchor " + file.name + ": " + repr(before[:105]) +
                           " count=" + str(body.count(before)))
    file.write_text(body.replace(before, after, 1), encoding="utf-8")


chat = TARGET / "developer_chat.py"
replace(chat, "import money_integrations\n",
        "import money_integrations\nimport payhip_store\nimport website_preview\nimport payhip_browser_agent\n")
replace(chat, "    match = _ENGINE.fullmatch(raw)\n",
        '''    browser_match = re.fullmatch(r"/project\\s+preview\\s+([A-Za-z0-9_-]+)\\s*", raw, re.I)
    if browser_match:
        return "project_preview", browser_match.group(1)
    match = _ENGINE.fullmatch(raw)
''')
replace(chat, '''        elif action == "money_mode":
            self._money(payload)
''',
        '''        elif action == "money_mode":
            self._money(payload)
        elif action == "project_preview":
            self._preview_saved_website(payload)
''')
replace(chat, '''        arguments = payload.split()
        if arguments[:1] == ["connect"]:
''',
        '''        arguments = payload.split()
        if arguments in (["payhip", "autopilot"], ["payhip", "create"]):
            if gaming_mode.enabled():
                self.say("Gaming Mode is ON. Type /engine gaming off before Payhip browser automation.")
                return
            self.say("Falcon will research Payhip's official guide, open its own Chrome "
                     "session, use local visual/DOM analysis and clicks, and save only "
                     "an Invisible draft. Sign in to Chrome once if prompted. "
                     "No financial changes, public publishing or password capture.")
            def work(cancel):
                return payhip_browser_agent.run_first_product(cancel=cancel)
            def complete(result):
                self.app.set_status("Ready • Payhip draft submitted")
                self.say("PAYHIP AUTOPILOT: " + result["status"] +
                         "\nPage: " + result["url"] +
                         "\nGuide: " + result["research_url"] +
                         "\n" + result["warning"])
            self._launch("Falcon is researching and building the Payhip listing…",
                         work, complete)
            return
        if arguments in (["payhip"], ["payhip", "start"], ["store"], ["store", "open"]):
            try:
                state = payhip_store.start_store()
            except (OSError, payhip_store.StoreError) as exc:
                self.say("Payhip store could not open: " + str(exc)[:230])
                return
            self.say("Opened official Payhip in your default browser and " +
                     ("created " if state["created"] else "reused ") +
                     "the local first-product draft: " + state["path"] + ". "
                     "No artwork has been generated, and nothing was published. "
                     "Sign in yourself and connect your payment provider using Payhip.")
            return
        if arguments[:1] == ["connect"]:
''')
replace(chat, "    def _engine(self, payload):\n",
        '''    def _preview_saved_website(self, name):
        if self.app.busy or self._running:
            self.say("Finish or STOP the current task before opening the website.")
            return
        try:
            website_preview.open_website(name)
        except (OSError, projects.ProjectError) as exc:
            self.say("Cannot preview saved website: " + str(exc)[:230])
            return
        self.say("Opened saved website in your default browser: " + name +
                 "/index.html. No PowerShell or second approval needed.")

    def _engine(self, payload):
''')

# This is AFTER an explicitly reviewed and approved site has been written to
# Falcon's workspace, so the browser preview can open without another prompt.
replace(chat, '''                 ". Nothing was executed, installed, or given PC permissions.")
''',
        '''                 ". Nothing was executed, installed, or given PC permissions.")
        if info["plan"]["kind"] == "website":
            try:
                website_preview.open_website(info["plan"]["name"])
            except (OSError, projects.ProjectError) as exc:
                self.say("Website saved, but the browser could not open automatically: " +
                         str(exc)[:230])
            else:
                self.say("Saved website opened automatically in your default browser.")
''')

# The developer source includes revision saving and backups. Open a preview
# after the reviewed change is successfully written, too.
replace(chat, '''                     "\\nNo generated code was executed.")
            return
        try:
            result = projects.save_approved(
''',
        '''                     "\\nNo generated code was executed.")
            if info["plan"]["kind"] == "website":
                try:
                    website_preview.open_website(info["plan"]["name"])
                except (OSError, projects.ProjectError) as exc:
                    self.say("Website revision saved; browser preview failed: " +
                             str(exc)[:230])
                else:
                    self.say("Updated website opened automatically in your default browser.")
            return
        try:
            result = projects.save_approved(
''')

palette = TARGET / "command_palette.py"
replace(palette, '        Command("Money Mode: local workflow integrations", "/money integrations"),\n',
        '''        Command("Money Mode: local workflow integrations", "/money integrations"),
        Command("Open Payhip and prepare digital art product", "/money payhip"),
        Command("Payhip AI browser autopilot (Invisible draft)", "/money payhip autopilot"),
        Command("Open reviewed website automatically", "/project preview "),
''')

# Clearly distinguish draft product metadata from completed, sellable art.
money = TARGET / "money_mode.py"
replace(money, '                "/money tools • /money seller <public_handle>\\n"\n',
        '                "/money tools • /money seller <public_handle>\\n"\n'
        '                "/money payhip  (open Payhip and prepare first product draft)\\n"\n')

for name in ("falcon.py", "falcon_launcher.py"):
    file = TARGET / name
    data = file.read_text(encoding="utf-8")
    if "V14.1.0" not in data:
        raise RuntimeError("Falcon V14.1 identity absent in " + name)
    file.write_text(data.replace("V14.1.0", "V14.2.0"), encoding="utf-8")
replace(TARGET / "RELEASE_VERSION.txt", PREVIOUS, VERSION)
replace(TARGET / "release_updates.py",
        "CURRENT_VERSION = (14, 1, 0)", "CURRENT_VERSION = (14, 2, 0)")
replace(RUNTIME / "app_updates.py",
        "CURRENT_VERSION = (14, 1, 0)", "CURRENT_VERSION = (14, 2, 0)")
replace(RUNTIME / "app_entry.py",
        "CURRENT_VERSION != (14, 1, 0)", "CURRENT_VERSION != (14, 2, 0)")
replace(RUNTIME / "app_entry.py",
        "version_file.read_text(encoding='utf-8').strip() != '14.1.0'",
        "version_file.read_text(encoding='utf-8').strip() != '14.2.0'")
replace(RUNTIME / "Falcon_Ai.iss",
        '#define MyAppVersion "14.1.0"', '#define MyAppVersion "14.2.0"')
iss = RUNTIME / "Falcon_Ai.iss"
raw = iss.read_text(encoding="utf-8")
if "falcon_app_v141_runtime" not in raw:
    raise RuntimeError("V14.1 installer icon path unexpectedly absent")
iss.write_text(raw.replace("falcon_app_v141_runtime", "falcon_app_v142_runtime"),
               encoding="utf-8")

foundation = TARGET / "falcon_foundation.py"
replace(foundation, 'VERSION = "14.1.0"', 'VERSION = "14.2.0"')
replace(foundation, 'if VERSION != "14.1.0":', 'if VERSION != "14.2.0":')
replace(foundation, '    Capability("trusted_updates", "Verified Windows updates", "available",',
        '''    Capability("payhip_browser_agent", "Payhip browser listing autopilot", "limited",
               "Runs owner-invoked Playwright + optional local visual analysis to prepare an "
               "Invisible listing, with STOP and no financial/public publication."),
    Capability("payhip_store", "Payhip digital product storefront", "limited",
               "Opens Payhip and creates a local listing draft. No Payhip login, upload or publishing."),
    Capability("website_auto_preview", "Approved website browser preview", "available",
               "Opens saved/approved Falcon HTML in default browser without a second prompt."),
    Capability("trusted_updates", "Verified Windows updates", "available",''')

entry = RUNTIME / "app_entry.py"
replace(entry, "    if '--falcon-money-self-test' in sys.argv:\n",
        '''    if '--falcon-store-self-test' in sys.argv:
        import website_preview, payhip_store, payhip_browser_agent
        if not callable(payhip_browser_agent.run_first_product):
            raise RuntimeError('Payhip browser automation missing')
        if payhip_browser_agent.PAYHIP_DASHBOARD != 'https://payhip.com/dashboard':
            raise RuntimeError('Payhip browser domain mismatch')
        if payhip_store.STORE_URL != 'https://payhip.com/':
            raise RuntimeError('Payhip site address unexpected')
        if not callable(website_preview.open_website):
            raise RuntimeError('Saved website browser preview missing')
        print('FALCON V14.2 PAYHIP STORE / PREVIEW CHECK PASSED')
        return 0
    if '--falcon-money-self-test' in sys.argv:
''')

(TARGET / "README_FALCON_AI_V14_2.txt").write_text(
    "Falcon AI V14.2.0 — Payhip Store Starter\n"
    "/money payhip opens https://payhip.com/ directly in the browser and "
    "creates a local first-product metadata draft (NOT completed artwork).\n"
    "Payhip is hosted online, not downloaded into Falcon. Sign in yourself, "
    "connect your own payment processor and publish reviewed product files.\n"
    "After reviewing and approving a saved website, Falcon automatically "
    "opens its local index.html without asking for separate browser approval.\n"
    "Use /project preview <name> to open an existing saved Falcon website.\n"
    "/money payhip autopilot reads official product setup guidance, runs real "
    "Chrome page interactions using an isolated Payhip login profile, uploads "
    "only known starter-pack files, verifies Invisible visibility and submits "
    "the seller-only listing. STOP cancels at action boundaries.\n"
    "Requires Google Chrome and the local wallpaper ZIP + cover in Downloads. "
    "Playwright browser tooling is bundled; first-time Payhip sign-in is manual.\n"
    "No customer credentials, Payhip API, live transactions or guaranteed "
    "earnings. Existing Ollama chat, STOP, Gaming Mode and Money Mode retained.\n",
    encoding="utf-8")

for name in ("payhip_store.py", "website_preview.py", "payhip_browser_agent.py", "money_mode.py",
             "customer_faq.py", "developer_chat.py"):
    if not (TARGET / name).is_file():
        raise RuntimeError("Falcon V14.2 missing module: " + name)
requirements = TARGET / "requirements.txt"
old_requirements = requirements.read_text(encoding="utf-8")
if "playwright" not in old_requirements.lower():
    requirements.write_text(old_requirements.rstrip() + "\nplaywright==1.56.0\n",
                            encoding="utf-8")
print("Staged Falcon V14.2 Payhip auto-open / self-guided browser agent candidate.")
