"""Offline tests for Falcon Payhip store opener and private product kit."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import payhip_store as store


class PayhipStarterTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "payhip_products"

    def test_opens_only_verified_payhip_url(self):
        mocked_browser = Mock(return_value=True)
        site = store.open_store(opener=mocked_browser)
        self.assertEqual(site, "https://payhip.com/")
        mocked_browser.assert_called_once_with("https://payhip.com/", new=2)

    def test_start_prepares_draft_and_opens_browser(self):
        browser = Mock(return_value=True)
        first = store.start_store(root=self.root, opener=browser)
        self.assertTrue(first["created"])
        self.assertFalse(first["ready_to_sell"])
        self.assertEqual(first["site"], "https://payhip.com/")
        saved = json.loads(
            (self.root / store.FIRST_PRODUCT / "PRODUCT_DRAFT.json").read_text(encoding="utf-8")
        )
        self.assertIn("NOT YET CREATED", saved["status"])
        self.assertEqual(len(saved["planned_artworks"]), 3)
        self.assertEqual(saved["suggested_price_usd"], "4.99")
        self.assertTrue((self.root / store.FIRST_PRODUCT /
                         "README_START_HERE.md").exists())
        self.assertEqual(browser.call_count, 1)

    def test_repeat_is_idempotent_and_preserves_owner_changes(self):
        browser = Mock(return_value=True)
        first = store.start_store(root=self.root, opener=browser)
        draft_file = Path(first["path"]) / "PRODUCT_DRAFT.json"
        orig = draft_file.read_text(encoding="utf-8")
        draft_file.write_text(orig + "\n ", encoding="utf-8")
        second = store.start_store(root=self.root, opener=browser)
        self.assertFalse(second["created"])
        self.assertEqual(draft_file.read_text(encoding="utf-8"), orig + "\n ")
        self.assertEqual(browser.call_count, 2)

    def test_browser_failure_is_clear_and_draft_survives(self):
        browser = Mock(return_value=False)
        with self.assertRaisesRegex(store.StoreError, "Default browser"):
            store.start_store(root=self.root, opener=browser)
        self.assertTrue((self.root / store.FIRST_PRODUCT / "PRODUCT_DRAFT.json").exists())

    def test_redirected_project_dir_never_followed(self):
        self.root.mkdir(parents=True)
        target = self.root.parent / "private"
        target.mkdir()
        try:
            (self.root / store.FIRST_PRODUCT).symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        browser = Mock(return_value=True)
        with self.assertRaises(store.StoreError):
            store.start_store(root=self.root, opener=browser)
        browser.assert_not_called()

    def test_no_account_login_or_secret_storage(self):
        joined = json.dumps(store.PRODUCT)
        self.assertNotIn("password", joined.lower())
        self.assertNotIn("api_key", joined.lower())
        self.assertNotIn("stripe_secret", joined.lower())
        self.assertNotIn("publish_url", joined.lower())


if __name__ == "__main__":
    unittest.main()
