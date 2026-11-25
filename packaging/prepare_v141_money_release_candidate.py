"""Stage Falcon 14.1.0 Money Mode in the existing trusted Windows packaging.

This only prepares candidate source and Inno Setup metadata. It never
installs, publishes, executes model-created files, or expands system rights.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/Falcon_Ai_MoneyMode_Candidate"
BASE_RUNTIME = ROOT / "build/falcon_app_coding_agent_runtime"
TARGET = ROOT / "build/Falcon_Ai_V14_1_Candidate"
RUNTIME = ROOT / "build/falcon_app_v141_runtime"
PREVIOUS = "14.0.0"
VERSION = "14.1.0"

if (BASE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != PREVIOUS:
    raise RuntimeError("Expected exact Falcon V14.0.0 source foundation")
if "CURRENT_VERSION = (14, 0, 0)" not in (BASE_RUNTIME / "app_updates.py").read_text():
    raise RuntimeError("Expected exact Falcon V14 updater foundation")
for directory in (TARGET, RUNTIME):
    if directory.exists():
        shutil.rmtree(directory)
shutil.copytree(BASE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copytree(BASE_RUNTIME, RUNTIME, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))


def replace(path, old, new):
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError("Ambiguous release version anchor: " + str(file) +
                           " count=" + str(text.count(old)) + " " + repr(old))
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


for file in ("falcon.py", "falcon_launcher.py"):
    source = TARGET / file
    data = source.read_text(encoding="utf-8")
    if "V14.0.0" not in data:
        raise RuntimeError("Missing Falcon 14 GUI/launcher identity: " + file)
    source.write_text(data.replace("V14.0.0", "V14.1.0"), encoding="utf-8")

replace(TARGET / "RELEASE_VERSION.txt", PREVIOUS, VERSION)
replace(TARGET / "release_updates.py",
        "CURRENT_VERSION = (14, 0, 0)", "CURRENT_VERSION = (14, 1, 0)")
replace(RUNTIME / "app_updates.py",
        "CURRENT_VERSION = (14, 0, 0)", "CURRENT_VERSION = (14, 1, 0)")
replace(RUNTIME / "app_entry.py",
        "CURRENT_VERSION != (14, 0, 0)", "CURRENT_VERSION != (14, 1, 0)")
replace(RUNTIME / "app_entry.py",
        "version_file.read_text(encoding='utf-8').strip() != '14.0.0'",
        "version_file.read_text(encoding='utf-8').strip() != '14.1.0'")
replace(RUNTIME / "Falcon_Ai.iss",
        '#define MyAppVersion "14.0.0"', '#define MyAppVersion "14.1.0"')

iss = RUNTIME / "Falcon_Ai.iss"
original = iss.read_text(encoding="utf-8")
if "falcon_app_v14_runtime" not in original:
    raise RuntimeError("Expected V14 runtime icon path in installer")
iss.write_text(original.replace("falcon_app_v14_runtime", "falcon_app_v141_runtime"),
               encoding="utf-8")

foundation = TARGET / "falcon_foundation.py"
raw = foundation.read_text(encoding="utf-8")
if raw.count('VERSION = "14.0.0"') != 1 or raw.count('if VERSION != "14.0.0":') != 1:
    raise RuntimeError("Foundation version contract changed")
raw = raw.replace('VERSION = "14.0.0"', 'VERSION = "14.1.0"').replace(
    'if VERSION != "14.0.0":', 'if VERSION != "14.1.0":')
old = '    Capability("trusted_updates", "Verified Windows updates", "available",'
if raw.count(old) != 1:
    raise RuntimeError("Foundation capability insertion anchor missing")
new = '''    Capability("money_orders", "Private Money Mode order tracking", "available",
               "Local user-provided briefs, prices, statuses and reply drafts. No account sync."),
    Capability("money_faq", "Customer FAQ demo builder", "limited",
               "Creates review-first static FAQ websites; no live agent or hosting."),
    Capability("money_workflows", "Local workflow webhooks", "limited",
               "Connect manually configured local n8n/Activepieces webhooks; "
               "no guaranteed downstream execution."),
    Capability("fiverr_account", "Live Fiverr seller account integration", "planned",
               "No authorized inbox, delivery or marketplace automation."),
'''
foundation.write_text(raw.replace(old, new + old, 1), encoding="utf-8")

entry = RUNTIME / "app_entry.py"
raw = entry.read_text(encoding="utf-8")
gate = "    if '--falcon-foundation-self-test' in sys.argv:\n"
if raw.count(gate) != 1:
    raise RuntimeError("Missing packaged self-test entry anchor")
money_gate = '''    if '--falcon-money-self-test' in sys.argv:
        import money_mode, money_integrations, customer_faq
        import falcon_foundation
        if not falcon_foundation.check_contract():
            raise RuntimeError('Money Mode foundation failed')
        if 'money_mode' not in money_mode.__name__:
            raise RuntimeError('Money Mode not bundled')
        if len(money_integrations.PROVIDERS) != 2:
            raise RuntimeError('Money Mode integration map incomplete')
        if not callable(customer_faq.make_faq_website):
            raise RuntimeError('Customer FAQ generator unavailable')
        print('FALCON V14.1 MONEY MODE PACKAGED CHECK PASSED')
        return 0
'''
entry.write_text(raw.replace(gate, money_gate + gate, 1), encoding="utf-8")

readme = TARGET / "README_FALCON_AI_V14_1.txt"
readme.write_text(
    "Falcon AI V14.1.0 — Money Mode Preview\n"
    "Local order tracking and reply drafts, client FAQ demo source, "
    "optional local n8n/Activepieces webhooks and OpenHands health check.\n"
    "Agent Fiverr and HustleBot were not installed or copied; "
    "only their order/proposal ideas were adapted locally.\n"
    "Website building still requires proposal review. Generated code is NOT run.\n"
    "Fiverr account data, messages, gigs and delivery are NOT automated.\n"
    "There is NO guarantee of sales or customer income.\n"
    "Existing Ollama model, Gaming Mode, STOP and updater retained.\n",
    encoding="utf-8")

required = ("money_mode.py", "money_integrations.py", "customer_faq.py",
            "project_coding_agent.py", "developer_chat.py", "falcon_foundation.py")
missing = [file for file in required if not (TARGET / file).is_file()]
if missing:
    raise RuntimeError("Money Mode release source missing: " + ", ".join(missing))
if (TARGET / "RELEASE_VERSION.txt").read_text().strip() != VERSION:
    raise RuntimeError("Version mismatch in new candidate")
if "CURRENT_VERSION = (14, 1, 0)" not in (RUNTIME / "app_updates.py").read_text():
    raise RuntimeError("Money Mode updater identity mismatch")
print("Staged Falcon V14.1.0 Money Mode Windows candidate. NO install or publish.")
