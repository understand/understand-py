import unittest
import json

from understand import CallbackHandler, RequestContext, UnderstandConfig, UnderstandLogger


class UnderstandLoggerTest(unittest.TestCase):
    def make_logger(self, config=None):
        sent = []
        logger = UnderstandLogger.from_config(
            config or UnderstandConfig(token="token", environment="test"),
            handler=CallbackHandler(lambda payload: sent.append(json.loads(payload))),
        )
        return logger, sent

    def test_log_adds_timestamp_metadata_and_context(self):
        logger, sent = self.make_logger()
        logger.field_provider.set_request_context(
            RequestContext(path="/hello", method="GET", client_ip="127.0.0.1")
        )

        result = logger.log("hello", level="info", context={"answer": 42})

        self.assertIsNone(result)
        event = sent[0]
        self.assertEqual(event["message"], "hello")
        self.assertEqual(event["level"], "info")
        self.assertEqual(event["context"], {"answer": 42})
        self.assertEqual(event["tags"], ["python_log"])
        self.assertEqual(event["env"], "test")
        self.assertEqual(event["url"], "/hello")
        self.assertEqual(event["client_ip"], "127.0.0.1")
        self.assertIsInstance(event["timestamp"], int)

    def test_boolean_message_is_formatted_like_laravel(self):
        logger, sent = self.make_logger()

        logger.log(False, level="warning")

        self.assertEqual(sent[0]["message"], "0")

    def test_ignored_logs_have_precedence_over_filter(self):
        config = UnderstandConfig(token="token", ignored_logs=("warning",), log_filter=lambda *_args: False)
        logger, sent = self.make_logger(config)

        result = logger.log("ignore me", level="warning")

        self.assertFalse(result)
        self.assertEqual(sent, [])

    def test_log_filter_true_suppresses_delivery(self):
        config = UnderstandConfig(token="token", log_filter=lambda level, message, context: message == "skip")
        logger, sent = self.make_logger(config)

        logger.log("send", level="error")
        result = logger.log("skip", level="error")

        self.assertFalse(result)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["message"], "send")

    def test_disabled_config_suppresses_delivery(self):
        logger, sent = self.make_logger(UnderstandConfig(token="token", enabled=False))

        result = logger.log("nope")

        self.assertFalse(result)
        self.assertEqual(sent, [])

    def test_exception_logs_error_event_with_group_id(self):
        logger, sent = self.make_logger()

        try:
            raise ValueError("bad value")
        except ValueError as exc:
            logger.exception(exc)

        event = sent[0]
        self.assertEqual(event["message"], "bad value")
        self.assertEqual(event["class"], "ValueError")
        self.assertEqual(event["level"], "error")
        self.assertEqual(event["tags"], ["py_error_log"])
        self.assertIn("group_id", event)
        self.assertIn("stack", event)

    def test_handler_exceptions_are_swallowed(self):
        def raise_error(_payload):
            raise RuntimeError("transport failure")

        logger = UnderstandLogger.from_config(
            UnderstandConfig(token="token"),
            handler=CallbackHandler(raise_error),
        )

        self.assertFalse(logger.log("hello"))

    def test_reset_context_regenerates_token_and_clears_collector(self):
        logger, _sent = self.make_logger()
        initial = logger.field_provider.token_provider.get_token()
        logger.field_provider.data_collector.set_in_array("sql_queries", {"query": "select 1"})

        logger.reset_context()

        self.assertNotEqual(logger.field_provider.token_provider.get_token(), initial)
        self.assertIsNone(logger.field_provider.data_collector.get_by_key("sql_queries"))

    def test_unknown_handler_type_raises_configuration_error(self):
        with self.assertRaises(ValueError):
            UnderstandLogger.from_config(UnderstandConfig(token="token", handler="queue"))
