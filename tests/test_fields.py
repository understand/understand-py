from datetime import datetime
import sys
import unittest
from unittest.mock import patch

from understand import DataCollector, FieldProvider, RequestContext, TokenProvider, UnderstandConfig


def make_provider(**config_overrides):
    config = UnderstandConfig(**config_overrides)
    collector = DataCollector()
    provider = FieldProvider(config=config, token_provider=TokenProvider(), data_collector=collector)
    return provider, collector


class FieldProviderTest(unittest.TestCase):
    def test_field_provider_resolves_custom_callbacks(self):
        provider, _collector = make_provider()
        provider.extend("get_test_value", lambda log: f"value:{log['message']}")

        data = provider.resolve_values({"custom_value": provider.get_test_value}, {"message": "hello"})

        self.assertEqual(data, {"custom_value": "value:hello"})

    def test_request_context_masks_hidden_query_and_body_fields(self):
        provider, _collector = make_provider()
        provider.set_request_context(
            RequestContext(
                path="api/users",
                method="POST",
                query={"search": "ormel", "password": "secret"},
                body={"email": "a@example.test", "access_token": "secret"},
            )
        )

        self.assertEqual(provider.get_url(), "/api/users")
        self.assertEqual(provider.get_request_method(), "POST")
        self.assertIsNone(provider.get_route_name())
        self.assertEqual(
            provider.get_query_string_array(),
            {"search": "ormel", "password": "[value hidden]"},
        )
        self.assertEqual(
            provider.get_request_body_data(),
            {"email": "a@example.test", "access_token": "[value hidden]"},
        )

    def test_request_context_respects_disabled_query_and_body_collection(self):
        provider, _collector = make_provider(query_string_enabled=False, request_body_enabled=False)
        provider.set_request_context(
            RequestContext(method="POST", query={"a": "b"}, body={"c": "d"})
        )

        self.assertIsNone(provider.get_query_string_array())
        self.assertIsNone(provider.get_request_body_data())

    def test_sql_queries_strip_bindings_by_default(self):
        provider, collector = make_provider()
        collector.set_in_array(
            "sql_queries",
            {"query": "SELECT 1 FROM users WHERE id = ?", "bindings": [123], "time": 1},
        )

        self.assertEqual(
            provider.get_sql_queries(),
            [{"query": "SELECT 1 FROM users WHERE id = ?", "time": 1}],
        )

    def test_sql_queries_merge_bindings_when_enabled(self):
        provider, collector = make_provider(sql_bindings=True)
        collector.set_in_array(
            "sql_queries",
            {
                "query": "SELECT ? FROM users WHERE active = ? AND created_at > ?",
                "bindings": [1, True, datetime(2026, 7, 19, 12, 30, 5)],
                "time": 1,
            },
        )

        self.assertEqual(
            provider.get_sql_queries(),
            [{"query": "SELECT 1 FROM users WHERE active = 1 AND created_at > 2026-07-19 12:30:05", "time": 1}],
        )

    def test_group_id_matches_laravel_examples(self):
        provider, _collector = make_provider()
        data = {
            "file": "app/Repositories/StripeWebhookRepository.php",
            "class": None,
            "line": 27,
        }

        self.assertEqual(provider.get_group_id(data), "1c1cf65bd2685193dca31e321f976512a6f1ea32")

        data["code"] = "0"
        self.assertEqual(provider.get_group_id(data), "1c1cf65bd2685193dca31e321f976512a6f1ea32")

        data["code"] = 12
        self.assertEqual(provider.get_group_id(data), "b500a4d4a363865e707c3bc95df8d4453e1ad8b1")

    def test_route_name_session_lookup_and_command_metadata(self):
        provider, _collector = make_provider()
        provider.set_request_context(
            RequestContext(route_name="users.show", session={"tenant_id": "acme"})
        )

        self.assertEqual(provider.get_route_name(), "users.show")
        self.assertEqual(provider.get_from_session("tenant_id"), "acme")

        with patch.object(sys, "argv", ["manage.py", "worker"]):
            self.assertEqual(provider.get_command(), "manage.py worker")
