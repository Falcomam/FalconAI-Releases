import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shorts_upload import validate_media, metadata, upload, digest

class UploadTests(unittest.TestCase):
    def test_media(self):
        data={"format":{"duration":"25"},"streams":[{"codec_type":"video","width":720,"height":1280},{"codec_type":"audio"}]}
        self.assertEqual(validate_media(data),25)
        data["format"]["duration"]="NaN"
        with self.assertRaises(ValueError): validate_media(data)
        data["format"]["duration"]="25"
        data["streams"].pop()
        with self.assertRaises(ValueError): validate_media(data)

    def test_metadata(self):
        future=dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=2)
        body=metadata("Title","Description","private",False,False,"23",future)
        self.assertEqual(body["status"]["privacyStatus"],"private")
        self.assertIn("publishAt",body["status"])
        with self.assertRaises(ValueError): metadata("Title","","public",False,False,"23",future)
        with self.assertRaises(ValueError): metadata("Title","","private",None,False,"23")

    def test_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=root/"draft.mp4"; path.write_bytes(b"reviewed bytes")
            (root/"REVIEW_REQUIRED.txt").touch()
            service=MagicMock()
            service.channels().list().execute.return_value={"items":[{"id":"channel","snippet":{"title":"Test"}}]}
            request=service.videos().insert.return_value
            request.next_chunk.return_value=(None,{"id":"abc"})
            service.videos().insert.reset_mock()
            body=metadata("Title","","private",False,False,"23")
            with self.assertRaises(RuntimeError):
                upload(service,root,"other",body,digest(path),str,lambda:False)
            with self.assertRaises(ValueError):
                upload(service,root,"channel",body,"bad",str,lambda:False)
            self.assertFalse((root/"upload_attempt.json").exists())
            self.assertEqual(upload(service,root,"channel",body,digest(path),str,lambda:False)["video_id"],"abc")
            with self.assertRaises(FileExistsError):
                upload(service,root,"channel",body,digest(path),str,lambda:False)
            self.assertEqual(service.videos().insert.call_count,1)

    def test_uncertain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=root/"draft.mp4"; path.write_bytes(b"video")
            (root/"REVIEW_REQUIRED.txt").touch()
            service=MagicMock()
            service.channels().list().execute.return_value={"items":[{"id":"channel","snippet":{"title":"Test"}}]}
            service.videos().insert.return_value.next_chunk.side_effect=TimeoutError
            with self.assertRaises(TimeoutError):
                upload(service,root,"channel",{},digest(path),str,lambda:False)
            self.assertEqual(json.loads((root/"upload_attempt.json").read_text())["state"],"pending_or_uncertain")
            with self.assertRaises(FileExistsError):
                upload(service,root,"channel",{},digest(path),str,lambda:False)

if __name__=="__main__":
    unittest.main()
