"""Stage Falcon Money Mode in the existing purple V14 coding-agent chat.

Development-only. Uses only local files. Never installs optional providers,
scrapes Fiverr, sends messages, runs generated code or publishes a Windows app.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "build" / "Falcon_Ai_CodingAgent_Candidate"
TARGET = ROOT / "build" / "Falcon_Ai_MoneyMode_Candidate"
if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "14.0.0":
    raise RuntimeError("Expected verified V14 coding-agent source candidate")
if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(ROOT / "packaging" / "money_mode.py", TARGET / "money_mode.py")
shutil.copy2(ROOT / "packaging" / "customer_faq.py", TARGET / "customer_faq.py")


def patch(name, old, new):
    file = TARGET / name
    data = file.read_text(encoding="utf-8")
    if data.count(old) != 1:
        raise RuntimeError(
            "Money Mode integration anchor mismatch " + name +
            " matches=" + str(data.count(old)) + " anchor=" + repr(old[:100]))
    file.write_text(data.replace(old, new, 1), encoding="utf-8")


patch("developer_chat.py",
      "import project_coding_agent as coding_agent\n",
      "import project_coding_agent as coding_agent\nimport money_mode\nimport customer_faq\n")
patch("developer_chat.py",
      "_ENGINE = re.compile(",
      '_MONEY = re.compile(r"^/money(?:\\s+(.*))?$", re.I | re.S)\n_ENGINE = re.compile(')
patch("developer_chat.py",
      "    match = _ENGINE.fullmatch(raw)\n",
      '''    money_match = _MONEY.fullmatch(raw)
    if money_match:
        return "money_mode", (money_match.group(1) or "help").strip()
    match = _ENGINE.fullmatch(raw)
''')
patch("developer_chat.py",
      '''        elif action == "engine":
            self._engine(payload)
''',
      '''        elif action == "engine":
            self._engine(payload)
        elif action == "money_mode":
            self._money(payload)
''')
patch("developer_chat.py",
      "    def _engine(self, payload):\n",
      '''    def _money(self, payload):
        if self.app.busy or self._running:
            self.say("Falcon is busy. Finish or press STOP before changing Money Mode orders.")
            return
        if payload.casefold() == "faq-demo":
            if self.pending:
                self.say("Review or reject the existing proposal before creating a demo.")
                return
            demo = customer_faq.make_faq_website(
                "falcon_faq_demo", "Northstar Demo Coffee",
                [
                    {"question": "What are your sample opening hours?",
                     "answer": "For this fictional demo, Monday–Friday, 9 a.m.–5 p.m."},
                    {"question": "Can you take online orders?",
                     "answer": "This fictional demonstration does not accept orders."},
                    {"question": "Do you offer catering?",
                     "answer": "Please contact the demo support team for information."},
                ],
                "demo@example.com")
            review = projects.review_proposal(demo)
            self.pending = {"plan": demo, "review": review, "reviewed": False}
            self.say("FICTIONAL CUSTOMER FAQ DEMO created as a source proposal only. "
                     "Use /project review and /project approve to save. "
                     "No server, deployment, chatbot service, customer message or paid API invoked.")
            return
        try:
            result = money_mode.handle_command(payload)
        except (OSError, money_mode.MoneyError) as exc:
            self.say("Money Mode: " + str(exc)[:290])
            return
        self.say(result)

    def _engine(self, payload):
''')
palette = TARGET / "command_palette.py"
raw = palette.read_text(encoding="utf-8")
mark = '        Command("Architect-first new project", "/project architect "),\n'
if raw.count(mark) != 1:
    raise RuntimeError("Money Mode command menu anchor changed")
raw = raw.replace(
    mark, mark +
    '        Command("Money Mode: new client order", "/money new "),\n'
    '        Command("Money Mode: saved orders", "/money list"),\n'
    '        Command("Money Mode: tools and handoffs", "/money tools"),\n'
    '        Command("Money Mode: example client FAQ site", "/money faq-demo"),\n', 1)
palette.write_text(raw, encoding="utf-8")
(TARGET / "MONEY_MODE_DEVELOPMENT_ONLY.txt").write_text(
    "Private local customer order tracking and draft/handoff foundation only.\n"
    "n8n, Activepieces, OpenHands, Agent Fiverr and HustleBot are NOT installed "
    "or connected; no Fiverr automation, code execution, or paid API enabled.\n",
    encoding="utf-8")
print("Staged Falcon Money Mode in same chat. No release, execution or installation.")
