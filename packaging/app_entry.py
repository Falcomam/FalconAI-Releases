"""Falcon Ai packaged application entry point.

The desktop EXE uses the verified *installer* updater instead of the old
source-folder swap. User data stays under %LOCALAPPDATA%\FalconAI.
"""
import sys

import app_updates
# Falcon's established UI looks up "release_updates" dynamically.
# Only inside the packaged app, redirect it to the new installer updater.
sys.modules['release_updates'] = app_updates

def main():
    if '--falcon-self-test' in sys.argv:
        import pathlib
        import falcon
        import falcon_launcher
        import status_dropdown
        import mini_monitor
        import notifications
        import agent
        import studio
        import ollama_runtime
        helper = pathlib.Path(getattr(sys, '_MEIPASS', pathlib.Path(__file__).parent)) / 'app_update_restart.ps1'
        if not helper.is_file():
            raise RuntimeError('Falcon Ai packaged update helper missing')
        if app_updates.CURRENT_VERSION != (13, 7, 0):
            raise RuntimeError('Wrong Falcon Ai installer version')
        print('FALCON AI PACKAGED APP SELF-TEST PASSED')
        return 0
    from falcon_launcher import main as launch
    return launch()

if __name__ == '__main__':
    raise SystemExit(main())
