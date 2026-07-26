from pathlib import Path
import os
import unittest
from unittest.mock import patch

from understand import UnderstandConfig


class UnderstandConfigTest(unittest.TestCase):
    def test_config_from_env_parses_understand_variables(self):
        env = {
            "UNDERSTAND_TOKEN": "token-123",
            "UNDERSTAND_ENABLED": "false",
            "UNDERSTAND_API_URL": "https://collector.example",
            "UNDERSTAND_HANDLER": "async",
            "UNDERSTAND_ENV": "production",
            "UNDERSTAND_SQL": "0",
            "UNDERSTAND_SQL_BINDINGS": "yes",
            "UNDERSTAND_QUERY_STRING": "no",
            "UNDERSTAND_REQUEST_BODY": "true",
            "UNDERSTAND_HIDDEN_REQUEST_FIELDS": "password,api_key",
        }
        with patch.dict(os.environ, env, clear=True):
            config = UnderstandConfig.from_env(project_root=Path("/tmp/project"))

        self.assertEqual(config.token, "token-123")
        self.assertFalse(config.enabled)
        self.assertEqual(config.api_url, "https://collector.example")
        self.assertEqual(config.handler, "async")
        self.assertEqual(config.environment, "production")
        self.assertFalse(config.sql_enabled)
        self.assertTrue(config.sql_bindings)
        self.assertFalse(config.query_string_enabled)
        self.assertTrue(config.request_body_enabled)
        self.assertEqual(config.hidden_fields, ("password", "api_key"))
        self.assertEqual(config.project_root, Path("/tmp/project"))

    def test_config_defaults_are_laravel_equivalent(self):
        config = UnderstandConfig()

        self.assertTrue(config.enabled)
        self.assertEqual(config.handler, "sync")
        self.assertTrue(config.sql_enabled)
        self.assertFalse(config.sql_bindings)
        self.assertTrue(config.query_string_enabled)
        self.assertTrue(config.request_body_enabled)
        self.assertIn("password_confirmation", config.hidden_fields)

    def test_config_accepts_laravel_post_data_alias_and_ssl_value(self):
        env = {
            "UNDERSTAND_POST_DATA": "false",
            "UNDERSTAND_SSL_CA_BUNDLE": "/tmp/ca.pem",
        }
        with patch.dict(os.environ, env, clear=True):
            config = UnderstandConfig.from_env()

        self.assertFalse(config.request_body_enabled)
        self.assertEqual(config.ssl_ca_bundle, "/tmp/ca.pem")
