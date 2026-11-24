"""Falcon-owned conversational style. No tools, accounts, file access, or agent privileges.

Only a small local preference is stored; no user conversations or private memories
are sent to GitHub. All safety/permission rules remain host-enforced.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

STORE = Path(os.getenv('LOCALAPPDATA') or Path.home()) / 'FalconAI' / 'personality.json'
MODES = ('casual', 'focused', 'quiet')
_STYLE = {
    'casual': (
        'Use a friendly, supportive, lightly playful style with the energy of a trusted '
        'coding buddy. Familiar greetings such as "brodie", "gang", or "YESSIR" and an '
        'occasional falcon/purple emoji are welcome when they fit the context, but do '
        'not force slang or repeat catchphrases every message. Be direct and useful. '
        'Celebrate verified progress, and treat troubleshooting calmly.'),
    'focused': (
        'Use a serious, clear, professional tone. No slang, hype, or decorative emoji. '
        'Keep diagnostic steps precise and concise.'),
    'quiet': (
        'Use brief neutral replies, minimal wording and no slang or decorative emoji. '
        'Include actionable steps when necessary.'),
}

def get_mode():
    try:
        data = json.loads(STORE.read_text(encoding='utf-8'))
        if isinstance(data, dict) and data.get('mode') in MODES:
            return data['mode']
    except (OSError, ValueError, TypeError):
        pass
    return 'casual'

def set_mode(mode):
    mode = str(mode).strip().lower()
    aliases = {'normal':'casual', 'default':'casual', 'friendly':'casual',
               'serious':'focused', 'professional':'focused', 'brief':'quiet'}
    mode = aliases.get(mode, mode)
    if mode not in MODES:
        raise ValueError('Choose casual, focused, or quiet')
    STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix('.tmp')
    tmp.write_text(json.dumps({'mode': mode}, sort_keys=True), encoding='utf-8')
    tmp.replace(STORE)
    return mode

def build_system_prompt(base, mode=None):
    mode = mode or get_mode()
    if mode not in MODES:
        mode = 'casual'
    return (str(base) + '\n\nFALCON CONVERSATION STYLE (' + mode.upper() + '): ' + _STYLE[mode] +
            '\nNever claim to be GPT-6, ChatGPT, Cipher, or a transferred model. '
            'You are Falcon AI using a selected conversational style. '
            'Never imply having memories you were not given or that an action ran without confirmation. '
            'Prioritize factual accuracy, task safety, and explicit user permission above personality. '
            'For emergencies, dangerous tasks, or critical debugging, be calm and precise. '
            'Conversation style is not authorization to execute tools, shell commands, or update software.')
