import logging
import json
import unittest

from understand import CallbackHandler, UnderstandConfig, UnderstandLogger
from understand.integrations.logging import UnderstandLoggingHandler


class LoggingIntegrationTest(unittest.TestCase):
    def make_handler(self):
        sent = []
        understand_logger = UnderstandLogger.from_config(
            UnderstandConfig(token="token"),
            handler=CallbackHandler(lambda payload: sent.append(json.loads(payload))),
        )
        return UnderstandLoggingHandler(understand_logger), sent

    def test_emit_sends_normal_logging_record(self):
        handler, sent = self.make_handler()
        record = logging.LogRecord(
            name="app",
            level=logging.WARNING,
            pathname=__file__,
            lineno=10,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )

        handler.emit(record)

        self.assertEqual(sent[0]["message"], "hello world")
        self.assertEqual(sent[0]["level"], "warning")
        self.assertEqual(sent[0]["context"]["logger_name"], "app")

    def test_emit_sends_exception_record(self):
        handler, sent = self.make_handler()

        try:
            raise RuntimeError("log boom")
        except RuntimeError:
            record = logging.getLogger("app").makeRecord(
                name="app",
                level=logging.ERROR,
                fn=__file__,
                lno=1,
                msg="failed",
                args=(),
                exc_info=True,
                func="test",
                extra=None,
            )
            handler.emit(record)

        self.assertEqual(sent[0]["message"], "log boom")
        self.assertEqual(sent[0]["class"], "RuntimeError")
        self.assertEqual(sent[0]["context"]["logger_name"], "app")
