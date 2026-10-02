import io
import json
import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

from rfr_markdown import build_request, read_paragraphs
from tests.test_markdown import FIXTURE, conflict


ROOT = Path(__file__).resolve().parents[1]
URI = "file:///example/test-statements.md"


def load_server():
    with patch.dict(os.environ, {"RFR_BACKEND": "local", "RFR_DEPTH": "1"}):
        module = runpy.run_path(str(ROOT / "red-factor-retract"), run_name="rfr_test")
    g = module["handle"].__globals__
    g["log"] = lambda *args: None
    return g


class MarkdownLSPTests(unittest.TestCase):
    def setUp(self):
        self.g = load_server()
        self.published = []
        self.requests = []
        self.result = {"diagnostics": [conflict()]}
        self.g["send_notification"] = lambda method, params: self.published.append((method, params))
        self.g["request_analysis"] = self.analyze
        self.g["call_llm"] = lambda *args: {"diagnostics": []}

    def analyze(self, payload, **kwargs):
        self.requests.append((payload, kwargs))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def open(self, text=FIXTURE, uri=URI, language="markdown", version=1):
        self.g["handle"]({"method": "textDocument/didOpen", "params": {
            "textDocument": {"uri": uri, "text": text, "languageId": language, "version": version},
        }})

    def latest(self):
        return self.published[-1][1]

    def test_open_change_save_corrects_conflict_and_retains_language(self):
        self.open()
        self.assertEqual(self.latest()["diagnostics"][0]["range"]["start"]["line"], 4)
        self.assertEqual(self.latest()["version"], 1)
        corrected = FIXTURE.replace("to OGG", "to MP3")
        self.result = {"diagnostics": []}
        self.g["handle"]({"method": "textDocument/didChange", "params": {
            "textDocument": {"uri": URI, "version": 2}, "contentChanges": [{"text": corrected}],
        }})
        self.assertEqual(self.g["docs"][URI]["languageId"], "markdown")
        self.g["handle"]({"method": "textDocument/didSave", "params": {"textDocument": {"uri": URI}}})
        self.assertEqual(self.latest()["diagnostics"], [])
        self.assertEqual(self.latest()["version"], 2)
        self.assertEqual(json.loads(self.requests[-1][0])["paragraphs"][1]["text"],
                         "For this renderer, set `output_format` to MP3.")

    def test_optional_save_text_is_used_without_resetting_version(self):
        self.open()
        self.result = {"diagnostics": []}
        corrected = FIXTURE.replace("to OGG", "to MP3")
        self.g["handle"]({"method": "textDocument/didSave", "params": {
            "textDocument": {"uri": URI}, "text": corrected,
        }})
        self.assertEqual(self.g["docs"][URI]["text"], corrected)
        self.assertEqual(self.g["docs"][URI]["languageId"], "markdown")
        self.assertEqual(self.latest()["version"], 1)

    def test_uri_extension_fallback_routes_markdown(self):
        for uri in ("file:///example/a.md", "file:///example/a.markdown", "file:///example/a.MD"):
            with self.subTest(uri=uri):
                self.open(uri=uri, language="")
                self.assertEqual(self.latest()["diagnostics"][0]["code"], "markdown-conflict")

    def test_initialize_advertises_save_and_close(self):
        replies = []
        self.g["send_response"] = lambda id_, result: replies.append(result)
        self.g["handle"]({"id": 1, "method": "initialize"})
        self.assertEqual(replies[0]["capabilities"]["textDocumentSync"],
                         {"openClose": True, "change": 1, "save": {"includeText": True}})

    def test_close_removes_buffer_and_clears_diagnostics(self):
        self.open()
        self.g["handle"]({"method": "textDocument/didClose", "params": {"textDocument": {"uri": URI}}})
        self.assertNotIn(URI, self.g["docs"])
        self.assertEqual(self.latest()["diagnostics"], [])

    def test_complete_input_limit_is_visible_and_does_not_request_a_prefix(self):
        self.result = {"diagnostics": []}
        self.open("a" * 6000)
        self.assertEqual(self.latest()["diagnostics"], [])
        self.assertEqual(len(json.loads(self.requests[0][0])["paragraphs"][0]["text"]), 6000)
        self.open("a" * 6001, version=2)
        d = self.latest()["diagnostics"][0]
        self.assertEqual(d["severity"], 3)
        self.assertIn("6,000", d["message"])
        self.assertIn("not analyzed", d["message"].lower())
        self.assertEqual(len(self.requests), 1)

    def test_backend_failure_clears_old_warning_and_can_retry(self):
        self.open()
        self.result = RuntimeError("synthetic backend failure")
        self.g["handle"]({"method": "workspace/executeCommand", "params": {
            "command": "redFactor.setDepth", "arguments": [2],
        }})
        self.assertEqual(self.latest()["diagnostics"][0]["severity"], 3)
        self.assertIn("failed", self.latest()["diagnostics"][0]["message"].lower())
        self.result = {"diagnostics": [conflict()]}
        self.g["infer_and_publish"](URI)
        self.assertEqual(self.latest()["diagnostics"][0]["severity"], 2)
        self.assertEqual(len(self.requests), 3)

    def test_invalid_response_is_not_cached_as_success(self):
        self.result = {"diagnostics": [{"paragraph": "invented"}]}
        self.open()
        self.assertIn("invalid", self.latest()["diagnostics"][0]["message"].lower())
        self.result = {"diagnostics": [conflict()]}
        self.g["infer_and_publish"](URI)
        self.assertEqual(self.latest()["diagnostics"][0]["code"], "markdown-conflict")

    def test_cache_is_document_and_depth_specific_and_publishes_current_version(self):
        self.open()
        self.g["docs"][URI]["version"] = 2
        self.g["infer_and_publish"](URI)
        self.assertEqual(self.latest()["version"], 2)
        self.assertEqual(len(self.requests), 1)
        other = "file:///example/other.md"
        self.open(uri=other)
        self.assertEqual(self.latest()["diagnostics"][0]["relatedInformation"][0]["location"]["uri"], other)
        self.assertEqual(len(self.requests), 2)
        self.g["depth"] = 2
        self.g["infer_and_publish"](URI)
        self.assertEqual(json.loads(self.requests[-1][0])["depth"], 2)
        self.assertEqual(len(self.requests), 3)

    def test_yaml_keeps_its_mapper_and_separate_cache(self):
        calls = []
        def yaml_analyze(text, change, depth):
            calls.append(text)
            return {"diagnostics": [{"path": "tts.format", "impact": .95, "severity": "error",
                                      "message": "synthetic format conflict"}]}
        self.g["call_llm"] = yaml_analyze
        self.open("tts:\n  format: ogg", uri="file:///example/config.yaml", language="yaml")
        self.assertEqual(self.latest()["diagnostics"][0]["severity"], 1)
        self.assertEqual(self.latest()["diagnostics"][0]["range"]["start"]["line"], 1)
        self.open("tts:\n  format: ogg")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(self.requests), 1)

    def test_matching_secrets_are_masked_before_markdown_transport(self):
        self.result = {"diagnostics": []}
        self.open("# Config\n\napi_key: SYNTHETIC_SECRET\n\nOther statement.")
        self.assertNotIn("SYNTHETIC_SECRET", self.requests[0][0])
        self.assertIn("[REDACTED]", self.requests[0][0])

    def test_masking_preserves_passage_identifiers_and_boundaries(self):
        self.result = {"diagnostics": []}
        self.open("api_key: SYNTHETIC_SECRET\n\nOnly MP3 is accepted.\n\nSelect OGG.")
        passages = json.loads(self.requests[0][0])["paragraphs"]
        self.assertEqual([p["id"] for p in passages], ["p1", "p2", "p3"])
        self.assertEqual(passages[2]["text"], "Select OGG.")

    def test_status_range_uses_utf16_for_first_character(self):
        self.result = RuntimeError("synthetic offline")
        self.open("😀 A claim.")
        self.assertEqual(self.latest()["diagnostics"][0]["range"]["end"], {"line": 0, "character": 2})

    def test_heading_only_document_does_not_need_inference(self):
        self.open("# Title\n\n```\nIgnored example.\n```\n")
        self.assertEqual(self.latest()["diagnostics"], [])
        self.assertEqual(self.requests, [])


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.g = load_server()
        self.g["get_openrouter_key"] = lambda: "synthetic-test-key"
        self.sent = []
        self.system, self.payload, self.schema = build_request(read_paragraphs(FIXTURE), 2)

    def response(self, req, timeout):
        self.sent.append((req.full_url, json.loads(req.data)))
        return io.BytesIO(json.dumps({"model": "synthetic-model", "choices": [
            {"message": {"content": json.dumps({"diagnostics": [conflict()]})}}
        ]}).encode())

    def request(self):
        return self.g["request_analysis"](self.payload, system_prompt=self.system, schema=self.schema)

    def test_local_backend_receives_markdown_schema_and_prompt(self):
        with patch("urllib.request.urlopen", side_effect=self.response):
            result = self.request()
        self.assertEqual(result["diagnostics"][0]["paragraph"], "p2")
        self.assertEqual(self.sent[0][1]["messages"][0]["content"], self.system)
        self.assertEqual(self.sent[0][1]["response_format"]["json_schema"]["schema"], self.schema)

    def test_hosted_schema_failure_retries_json_object(self):
        self.g["BACKEND"] = "openrouter"
        def respond(req, timeout):
            if not self.sent:
                self.sent.append((req.full_url, json.loads(req.data)))
                raise RuntimeError("synthetic schema rejection")
            return self.response(req, timeout)
        with patch("urllib.request.urlopen", side_effect=respond):
            self.request()
        self.assertEqual(self.sent[0][1]["messages"][0]["content"], self.system)
        self.assertEqual(self.sent[0][1]["response_format"]["json_schema"]["schema"], self.schema)
        self.assertEqual(self.sent[1][1]["response_format"], {"type": "json_object"})

    def test_json_object_retry_retains_the_explicit_markdown_contract(self):
        self.g["BACKEND"] = "openrouter"
        def respond(req, timeout):
            if not self.sent:
                self.sent.append((req.full_url, json.loads(req.data)))
                raise RuntimeError("synthetic schema rejection")
            return self.response(req, timeout)
        with patch("urllib.request.urlopen", side_effect=respond):
            self.request()
        fallback_prompt = self.sent[1][1]["messages"][0]["content"]
        self.assertIn(json.dumps(self.schema), fallback_prompt)
        self.assertIn("instruction", fallback_prompt)

    def test_auto_falls_back_to_local_with_markdown_contract(self):
        self.g["BACKEND"] = "auto"
        def respond(req, timeout):
            if req.full_url == self.g["OR_URL"]:
                self.sent.append((req.full_url, json.loads(req.data)))
                raise RuntimeError("synthetic hosted failure")
            return self.response(req, timeout)
        with patch("urllib.request.urlopen", side_effect=respond):
            self.request()
        self.assertEqual([url for url, _ in self.sent], [self.g["OR_URL"], self.g["OR_URL"], self.g["LLM_URL"]])
        self.assertEqual(self.sent[-1][1]["messages"][0]["content"], self.system)
        self.assertEqual(self.sent[-1][1]["response_format"]["json_schema"]["schema"], self.schema)

    def test_local_failure_is_raised_after_json_object_retry(self):
        def respond(req, timeout):
            self.sent.append((req.full_url, json.loads(req.data)))
            raise RuntimeError("synthetic offline")
        with patch("urllib.request.urlopen", side_effect=respond), self.assertRaises(RuntimeError):
            self.request()
        self.assertEqual([body["response_format"]["type"] for _, body in self.sent], ["json_schema", "json_object"])

    def test_hosted_only_exhaustion_is_raised_without_local_call(self):
        self.g["BACKEND"] = "openrouter"
        def respond(req, timeout):
            self.sent.append((req.full_url, json.loads(req.data)))
            raise RuntimeError("synthetic hosted failure")
        with patch("urllib.request.urlopen", side_effect=respond), self.assertRaises(RuntimeError):
            self.request()
        self.assertEqual([url for url, _ in self.sent], [self.g["OR_URL"], self.g["OR_URL"]])

    def test_yaml_transport_still_sends_yaml_schema(self):
        with patch("urllib.request.urlopen", side_effect=self.response):
            self.g["call_llm"]("tts:\n  format: ogg", "save", 1)
        self.assertEqual(self.sent[0][1]["messages"][0]["content"], self.g["SYSTEM_PROMPT"])
        self.assertEqual(self.sent[0][1]["response_format"]["json_schema"]["schema"], self.g["SCHEMA"])


if __name__ == "__main__":
    unittest.main()
