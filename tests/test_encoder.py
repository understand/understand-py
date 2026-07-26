from pathlib import Path
import tempfile
import unittest

from understand import ExceptionEncoder, UnderstandConfig


class ExceptionEncoderTest(unittest.TestCase):
    def test_exception_to_dict_encodes_exception_details(self):
        config = UnderstandConfig(project_root=Path.cwd())
        encoder = ExceptionEncoder(config=config)

        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            encoded = encoder.exception_to_dict(exc)

        self.assertEqual(encoded["message"], "boom")
        self.assertEqual(encoded["class"], "RuntimeError")
        self.assertIsNone(encoded["code"])
        self.assertTrue(encoded["file"].endswith("tests/test_encoder.py"))
        self.assertIsInstance(encoded["line"], int)
        self.assertGreaterEqual(len(encoded["stack"]), 1)
        self.assertIn("function", encoded["stack"][0])

    def test_exception_message_falls_back_to_class_name(self):
        encoder = ExceptionEncoder()

        try:
            raise RuntimeError()
        except RuntimeError as exc:
            encoded = encoder.exception_to_dict(exc)

        self.assertEqual(encoded["message"], "RuntimeError")

    def test_exception_to_dict_rejects_non_exception(self):
        encoder = ExceptionEncoder()

        with self.assertRaises(TypeError):
            encoder.exception_to_dict("not an exception")

    def test_stack_trace_limit_is_applied(self):
        encoder = ExceptionEncoder(UnderstandConfig(stack_trace_limit=1))

        try:
            raise RuntimeError("limited")
        except RuntimeError as exc:
            encoded = encoder.exception_to_dict(exc)

        self.assertEqual(len(encoded["stack"]), 1)

    def test_get_code_returns_source_snippet(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snippet.py"
            path.write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")
            encoder = ExceptionEncoder(UnderstandConfig(project_root=Path(tmp)))

            snippet = encoder.get_code("snippet.py", 2, lines_around=1)

        self.assertEqual(
            snippet,
            [
                {"line": 1, "code": "one"},
                {"line": 2, "code": "two"},
                {"line": 3, "code": "three"},
            ],
        )

    def test_set_current_stack_trace_adds_file_line_and_stack(self):
        encoder = ExceptionEncoder(UnderstandConfig(project_root=Path.cwd()))

        encoded = encoder.set_current_stack_trace({"message": "plain log"})

        self.assertEqual(encoded["message"], "plain log")
        self.assertIn("stack", encoded)
        self.assertIn("file", encoded)
        self.assertIn("line", encoded)

