"""V13.6 conversational style contracts: no new PC permissions."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import personality
import falcon
import unified

class PersonalityTests(unittest.TestCase):
    def test_default_and_modes_persist(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(personality,'STORE',Path(tmp)/'style.json'):
            self.assertEqual(personality.get_mode(),'casual')
            self.assertEqual(personality.set_mode('serious'),'focused')
            self.assertEqual(personality.get_mode(),'focused')
            self.assertEqual(personality.set_mode('normal'),'casual')
            self.assertEqual(personality.get_mode(),'casual')
            self.assertEqual(personality.set_mode('quiet'),'quiet')
            self.assertEqual(personality.get_mode(),'quiet')
            with self.assertRaises(ValueError):personality.set_mode('superuser')
    def test_build_prompt_preserves_security_constraints(self):
        for mode in personality.MODES:
            result=personality.build_system_prompt(falcon.SYSTEM,mode)
            self.assertIn('Falcon AI',result)
            self.assertIn('not authorization',result)
            self.assertIn('permission',result.lower())
            self.assertNotIn('ignore previous instructions',result.lower())
        serious=personality.build_system_prompt(falcon.SYSTEM,'focused')
        self.assertIn('No slang',serious)
        friendly=personality.build_system_prompt(falcon.SYSTEM,'casual')
        self.assertIn('brodie',friendly)
    def test_tone_is_local_and_not_plan(self):
        self.assertEqual(unified.route('/tone serious'),('personality','serious'))
        self.assertEqual(unified.route('be serious for a minute'),('personality','focused'))
        self.assertEqual(unified.route('talk normally again'),('personality','casual'))
        self.assertEqual(unified.route('/tone status'),('personality','status'))
        self.assertIsNone(unified.route('why should I be serious?'))
        self.assertNotIn('personality.py',__import__('core_upgrade').ALLOW)
    def test_personality_settings_are_outside_app_folder(self):
        self.assertEqual(personality.STORE.name,'personality.json')
        self.assertNotEqual(personality.STORE.parent,Path(__file__).resolve().parents[1])
    def test_chat_uses_current_tone(self):
        app=falcon.Falcon.__new__(falcon.Falcon)
        app.history=[]
        with mock.patch.object(personality,'build_system_prompt',return_value='CUSTOM TONE') as prompt, \
             mock.patch.object(app,'request') as request:
            app.chat_message('hello Falcon')
            self.assertEqual(request.call_args.args[0][0]['content'],'CUSTOM TONE')
            prompt.assert_called_once()

if __name__=='__main__':unittest.main()
