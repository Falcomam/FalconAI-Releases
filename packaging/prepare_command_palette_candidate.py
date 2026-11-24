"""Stage one-chat Tab completion + organized Commands button in Falcon Ai.

Builds on the tested v13.8.0 and next-update Copy Reply candidate. No new
version, release asset or installer is published by this development step.
"""
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "build" / "Falcon_Ai_CopyReply_Candidate"
TARGET = REPO / "build" / "Falcon_Ai_CommandPalette_Candidate"

if (SOURCE / "RELEASE_VERSION.txt").read_text(encoding="utf-8").strip() != "13.8.0":
    raise RuntimeError("Verified V13.8.0 copy-reply candidate source is required")
if TARGET.exists():
    shutil.rmtree(TARGET)
shutil.copytree(SOURCE, TARGET, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
shutil.copy2(REPO / "packaging" / "command_palette.py", TARGET / "command_palette.py")


def replace_one(path, old, new):
    dest = TARGET / path
    raw = dest.read_text(encoding="utf-8")
    found = raw.count(old)
    if found != 1:
        raise RuntimeError(f"Falcon command UI anchor changed in {path}: {old[:90]!r}, count={found}")
    dest.write_text(raw.replace(old, new, 1), encoding="utf-8")


replace_one("falcon.py",
            "import message_copy\n",
            "import message_copy\nimport command_palette\n")
replace_one("falcon.py",
            "        inputrow = tk.Frame(composer, bg=C['base'])\n",
            """        self.command_hint = tk.Label(
            composer, text='TAB completes /commands  •  ⌘ Commands opens shortcuts',
            bg=C['base'], fg=C['muted'], font=('Segoe UI', 8), anchor='w')
        self.command_hint.pack(fill='x', pady=(0, 5))
        inputrow = tk.Frame(composer, bg=C['base'])
""")
replace_one("falcon.py",
            "        self.entry.bind('<Return>', lambda e: self.send())\n"
            "        button(inputrow, 'SEND  ➜', self.send, primary=True, pad_y=12).pack(side='left', padx=(0, 8))",
            """        self.entry.bind('<Return>', lambda e: self.send())
        self.command_picker = command_palette.EntryController(self.entry, self.command_hint)
        # An organized native menu inserts a command in the SAME composer.
        # It does not submit, run a PC action or approve any proposal.
        command_button = tk.Menubutton(
            inputrow, text='⌘ Commands ▾', bg=C['panel2'], fg=C['text'],
            activebackground=C['purple_deep'], activeforeground=C['text'],
            relief='flat', borderwidth=0, cursor='hand2',
            font=('Segoe UI', 9, 'bold'), padx=11, pady=10)
        command_menu = tk.Menu(
            command_button, tearoff=0, bg=C['panel'], fg=C['text'],
            activebackground=C['purple_deep'], activeforeground=C['text'])
        for section, commands in command_palette.GROUPS:
            section_menu = tk.Menu(
                command_menu, tearoff=0, bg=C['panel'], fg=C['text'],
                activebackground=C['purple_deep'], activeforeground=C['text'])
            for item in commands:
                section_menu.add_command(
                    label=item.label, command=lambda command=item.insert:
                    self.command_picker.insert(command))
            command_menu.add_cascade(label=section, menu=section_menu)
        command_button.configure(menu=command_menu)
        command_button.pack(side='left', padx=(0, 8))
        button(inputrow, 'SEND  ➜', self.send, primary=True, pad_y=12).pack(side='left', padx=(0, 8))""")
(TARGET / "COMMAND_PALETTE_CANDIDATE_ONLY.txt").write_text(
    "Minecraft-style Tab/Shift+Tab command completion and Commands menu "
    "integrated into Falcon's original chat composer. Shortcuts insert text "
    "but never execute PC actions, approve code or install models. "
    "Development candidate only, no released installer.\n",
    encoding="utf-8",
)
print("Prepared in-chat Tab autocomplete and categorized command picker candidate")
