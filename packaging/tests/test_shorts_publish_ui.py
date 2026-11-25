import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shorts_publish_ui import oauth_config, plan_upload
from shorts_controls import MoneyControls, set_enabled


class PublishUITests(unittest.TestCase):
    def test_review_and_metadata(self):
        args = ('Title', 'Description', 'private', 'no', 'yes', '23', '')
        for certified, previewed in ((False, True), (True, False), (False, False)):
            with self.assertRaises(ValueError):
                plan_upload(*args, certified, previewed)
        body = plan_upload(*args, True, True)
        self.assertEqual(body['status']['privacyStatus'], 'private')
        self.assertTrue(body['status']['containsSyntheticMedia'])
        with self.assertRaises(ValueError):
            plan_upload('Title', '', 'private', '', 'no', '23', '', True, True)
        future = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)).isoformat()
        scheduled = plan_upload('Title', '', 'private', 'no', 'no', '23', future, True, True)
        self.assertIn('publishAt', scheduled['status'])

    def test_oauth_config_restricts_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'client.json'
            config = {'installed': {'client_id': 'fixture.apps.googleusercontent.com',
                       'client_secret': 'test-only',
                       'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                       'token_uri': 'https://oauth2.googleapis.com/token',
                       'redirect_uris': ['http://localhost']}}
            path.write_text(json.dumps(config), encoding='utf-8')
            self.assertNotIn('redirect_uris', oauth_config(path)['installed'])
            for field in ('auth_uri', 'token_uri'):
                original = config['installed'][field]
                config['installed'][field] = 'https://example.invalid/'
                path.write_text(json.dumps(config), encoding='utf-8')
                with self.assertRaises(ValueError):
                    oauth_config(path)
                config['installed'][field] = original

    def test_scheduler_respects_review_and_session_pause(self):
        with tempfile.TemporaryDirectory() as tmp:
            controls = MoneyControls.__new__(MoneyControls)
            controls.root = Path(tmp)
            controls.window = MagicMock()
            controls.features = MagicMock()
            controls.features.app.busy = False
            controls.features._running = False
            controls.last_attempt = None
            controls.review_active = True
            controls.session_paused = False
            set_enabled(True, controls.root)
            fake_gaming = SimpleNamespace(enabled=lambda: False)
            with patch.dict(sys.modules, {'gaming_mode': fake_gaming}), patch('shorts_controls.due', return_value=True):
                controls.tick()
                controls.features._shorts_draft.assert_not_called()
                controls.review_active = False
                controls.session_paused = True
                controls.tick()
                controls.features._shorts_draft.assert_not_called()
                controls.session_paused = False
                controls.tick()
                controls.tick()
                controls.features._shorts_draft.assert_called_once()

    def test_pause_with_preference_write_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            controls = MoneyControls.__new__(MoneyControls)
            controls.root = Path(tmp)
            controls.choice = MagicMock()
            controls.features = MagicMock()
            controls.session_paused = False
            with patch('shorts_controls.set_enabled', side_effect=OSError):
                controls.pause()
            self.assertTrue(controls.session_paused)
            controls.features.stop.assert_called_once()


if __name__ == '__main__':
    unittest.main()
