import json
import unittest
from unittest.mock import patch

from understand import CallbackHandler, SyncHandler, UnderstandConfig


class HandlersTest(unittest.TestCase):
    def test_callback_handler_serializes_payload_to_json(self):
        sent = []
        handler = CallbackHandler(lambda payload: sent.append(payload))

        response = handler.handle({"message": "hello"})

        self.assertEqual(json.loads(sent[0]), {"message": "hello"})
        self.assertIsNone(response)

    def test_callback_handler_parses_json_response(self):
        handler = CallbackHandler(lambda _payload: '{"ok": true}')

        self.assertEqual(handler.handle({"message": "hello"}), {"ok": True})

    def test_base_endpoint_joins_api_url_and_token(self):
        handler = CallbackHandler(lambda _payload: None, config=UnderstandConfig(token="abc", api_url="https://example.test/"))

        self.assertEqual(handler.get_endpoint(), "https://example.test/abc")

    def test_sync_handler_uses_configured_ca_bundle(self):
        handler = SyncHandler(UnderstandConfig(token="abc", ssl_ca_bundle="/tmp/ca.pem"))

        with patch("understand.handlers.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b'{"ok": true}'

            response = handler.handle({"message": "hello"})

        self.assertEqual(response, {"ok": True})
        self.assertEqual(urlopen.call_args.kwargs["cafile"], "/tmp/ca.pem")
