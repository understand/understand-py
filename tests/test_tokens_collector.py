import unittest

from understand import DataCollector, TokenProvider


class TokenProviderAndDataCollectorTest(unittest.TestCase):
    def test_token_provider_returns_stable_token_until_regenerated(self):
        provider = TokenProvider()
        initial = provider.get_token()

        self.assertTrue(initial)
        self.assertEqual(provider.get_token(), initial)

        provider.generate()

        self.assertNotEqual(provider.get_token(), initial)

    def test_data_collector_limits_array_entries(self):
        collector = DataCollector(limit=1)

        collector.set_in_array("sql_queries", {"query": "select 1"})
        collector.set_in_array("sql_queries", {"query": "select 2"})

        self.assertEqual(collector.get_by_key("sql_queries"), [{"query": "select 2"}])

    def test_data_collector_reset_clears_data(self):
        collector = DataCollector()
        collector.set("env", "test")

        collector.reset()

        self.assertIsNone(collector.get_by_key("env"))
