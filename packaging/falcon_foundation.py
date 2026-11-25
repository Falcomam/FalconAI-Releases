"""Falcon AI V14 foundation: truthful capability contracts and safe status.

This module never invokes a language model, runs source code, touches Windows
settings, downloads anything, or changes user data. It describes only the
capability boundaries that the V14 candidate must be tested against.
"""
from __future__ import annotations

from dataclasses import dataclass

VERSION = "14.0.0"
STATUS = frozenset({"available", "limited", "planned"})


@dataclass(frozen=True)
class Capability:
    key: str
    label: str
    state: str
    explanation: str
    user_approval: bool = False

    def __post_init__(self):
        if not self.key or not self.label or not self.explanation:
            raise ValueError("Capability description cannot be blank")
        if self.state not in STATUS:
            raise ValueError("Invalid capability state")


CAPABILITIES = (
    Capability("local_chat", "Local Ollama chat", "available",
               "Needs Ollama running and an installed chat model."),
    Capability("source_projects", "Create source-code projects", "available",
               "Generates proposed files; checks and saves only with full review.",
               user_approval=True),
    Capability("source_revisions", "Review/edit saved projects", "available",
               "Changes require diff review, explicit approval and backups.",
               user_approval=True),
    Capability("coding_model", "Independent coding model", "available",
               "Select an already installed coding model without changing chat."),
    Capability("gaming_mode", "Gaming Mode", "available",
               "Pauses new AI work; best-effort unloads selected loaded models. "
               "Does not guarantee FPS or change GPU settings."),
    Capability("trusted_updates", "Verified Windows updates", "available",
               "Installer updates require a newer trusted release and consent.",
               user_approval=True),
    Capability("static_validation", "Source static checks", "limited",
               "Syntax, fingerprints and website heuristics; not runtime tests."),
    Capability("self_improvement", "Review-first source improvement", "limited",
               "Development review tools exist; frozen-EXE self-patching is disabled.",
               user_approval=True),
    Capability("isolated_project_tests", "Run generated projects in isolation", "planned",
               "Requires a separately reviewed sandbox and execution consent.",
               user_approval=True),
    Capability("browser_visual_critic", "Rendered website critic", "planned",
               "Real browser screenshot comparison has not been implemented."),
    Capability("fabric_mod_builds", "Build/compile Minecraft mods", "planned",
               "Source starters do not mean a compiled, tested Fabric mod.",
               user_approval=True),
    Capability("autonomous_app_install", "Install generated apps autonomously", "planned",
               "Generated programs must never silently execute or install.",
               user_approval=True),
)

BY_KEY = {item.key: item for item in CAPABILITIES}


def check_contract():
    """Fail closed if future developers accidentally corrupt capability data."""
    if len(BY_KEY) != len(CAPABILITIES):
        raise ValueError("Duplicated capability key")
    if VERSION != "14.0.0":
        raise ValueError("Unexpected V14 foundation contract version")
    for item in CAPABILITIES:
        if item.state == "planned" and "installed" in item.explanation.lower():
            raise ValueError("Planned capability must not imply installed functionality")
    return True


def render_status(*, gaming=None, coding_model=None):
    """User-facing on-device summary; configured models aren't runtime-tested."""
    check_contract()
    lines = ["FALCON FOUNDATION V" + VERSION,
             "One local Windows assistant; source approvals are not execution consent.",
             "Capabilities (available means an implemented interface, not a "
             "guarantee a local model/service is working):"]
    for item in CAPABILITIES:
        lines.append("- " + item.label + ": " + item.state.upper() +
                     " — " + item.explanation)
    if type(gaming) is bool:
        lines.append("Saved Gaming Mode: " + ("ON (AI paused)" if gaming else "OFF"))
    if isinstance(coding_model, str) and coding_model:
        lines.append("Configured coding model (installation not checked): " +
                     coding_model[:120])
    lines.append("Nothing was run, modified, installed or downloaded by this status check.")
    return "\n".join(lines)
