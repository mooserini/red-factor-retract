from pathlib import Path
import json
import unittest

from rfr_markdown import build_request, map_contradictions, paragraph_range, read_paragraphs


FIXTURE = (Path(__file__).resolve().parents[1] / "test-statements.md").read_text()


def conflict():
    return {
        "paragraph": "p2", "conflicts_with": "p1",
        "quote": "set `output_format` to OGG",
        "conflicting_quote": "accepts only MP3 and WAV",
        "message": "The OGG instruction violates the stated accepted output formats.",
    }


class ParagraphTests(unittest.TestCase):
    def test_fixture_paragraphs_and_instruction_range(self):
        paragraphs = read_paragraphs(FIXTURE)
        self.assertEqual([p.text for p in paragraphs], [
            "The renderer accepts only MP3 and WAV output.",
            "For this renderer, set `output_format` to OGG.",
            "OGG support might be added in a future version.",
        ])
        self.assertEqual(paragraphs[1].heading, "Example output configuration")
        self.assertEqual(paragraph_range(FIXTURE, paragraphs[1]), {
            "start": {"line": 4, "character": 0},
            "end": {"line": 4, "character": 46},
        })

    def test_identical_paragraphs_have_distinct_ids_and_locations(self):
        paragraphs = read_paragraphs("Same claim.\n\nSame claim.\n")
        self.assertEqual([p.id for p in paragraphs], ["p1", "p2"])
        self.assertEqual([p.start_line for p in paragraphs], [0, 2])

    def test_crlf_multiline_paragraph_has_utf16_end_column(self):
        text = "# Title\r\n\r\nFirst line\r\nnext 😀\r\n"
        paragraphs = read_paragraphs(text)
        self.assertEqual(paragraphs[0].text, "First line\nnext 😀")
        self.assertEqual(paragraph_range(text, paragraphs[0]), {
            "start": {"line": 2, "character": 0},
            "end": {"line": 3, "character": 7},
        })

    def test_atx_and_setext_headings_are_context_not_claims(self):
        text = "Title\n=====\n\nClaim one.\n\n## Scope ##\nClaim two.\n"
        paragraphs = read_paragraphs(text)
        self.assertEqual([p.text for p in paragraphs], ["Claim one.", "Claim two."])
        self.assertEqual([p.heading for p in paragraphs], ["Title", "Title / Scope"])

    def test_fenced_code_is_excluded_and_prose_resumes(self):
        for fence in ("```", "~~~~"):
            with self.subTest(fence=fence):
                text = "Claim.\n" + fence + "python\n# Not a heading\nFalse claim.\n" + fence + "\nOther claim."
                self.assertEqual([p.text for p in read_paragraphs(text)], ["Claim.", "Other claim."])

    def test_shorter_fence_does_not_close_block(self):
        text = "````\nIgnored.\n```\nStill ignored.\n````\nActual claim."
        self.assertEqual([p.text for p in read_paragraphs(text)], ["Actual claim."])

    def test_unclosed_fence_excludes_rest_of_document(self):
        self.assertEqual([p.text for p in read_paragraphs("Claim.\n\n~~~\nIgnored forever.")], ["Claim."])

    def test_blank_document_has_no_claims(self):
        self.assertEqual(read_paragraphs(" \n\n"), [])


class ContradictionTests(unittest.TestCase):
    def setUp(self):
        self.paragraphs = read_paragraphs(FIXTURE)
        self.uri = "file:///example/test-statements.md"

    def map(self, result):
        return map_contradictions(FIXTURE, self.paragraphs, result, self.uri)

    def test_supported_conflict_highlights_instruction_and_references_restriction(self):
        diagnostics = self.map({"diagnostics": [conflict()]})
        self.assertEqual(len(diagnostics), 1)
        d = diagnostics[0]
        self.assertEqual(d["severity"], 2)
        self.assertEqual(d["range"]["start"], {"line": 4, "character": 0})
        self.assertTrue(d["message"].startswith("Conflicts with the statement on line 3"))
        self.assertIn("accepts only MP3 and WAV", d["message"])
        self.assertIn("set `output_format` to OGG", d["message"])
        self.assertEqual(d["relatedInformation"][0]["location"]["uri"], self.uri)
        self.assertEqual(d["relatedInformation"][0]["location"]["range"]["start"]["line"], 2)

    def test_success_with_no_conflicts_returns_empty_diagnostics(self):
        self.assertEqual(self.map({"diagnostics": []}), [])

    def test_invalid_evidence_or_shape_is_rejected(self):
        for field, value in [
            ("paragraph", "invented"), ("conflicts_with", "p2"),
            ("quote", "never in the document"), ("conflicting_quote", ""),
            ("message", 42), ("message", ""), ("paragraph", None),
        ]:
            with self.subTest(field=field, value=value):
                entry = conflict()
                entry[field] = value
                with self.assertRaises(ValueError):
                    self.map({"diagnostics": [entry]})
        for result in [[], {}, {"diagnostics": {}}, {"diagnostics": [None]},
                       {"diagnostics": [{"paragraph": "p2"}]}]:
            with self.subTest(result=result), self.assertRaises(ValueError):
                self.map(result)

    def test_duplicate_pair_is_only_published_once(self):
        self.assertEqual(len(self.map({"diagnostics": [conflict(), conflict()]})), 1)

    def test_request_carries_exact_passages_and_context_without_yaml_constraints(self):
        system, payload, schema = build_request(self.paragraphs, 2)
        data = json.loads(payload)
        self.assertEqual(data["depth"], 2)
        self.assertEqual(data["paragraphs"][1]["id"], "p2")
        self.assertEqual(data["paragraphs"][1]["text"], "For this renderer, set `output_format` to OGG.")
        self.assertEqual(data["paragraphs"][1]["heading"], "Example output configuration")
        self.assertNotIn("constraints", data)
        self.assertEqual(set(schema["properties"]["diagnostics"]["items"]["required"]),
                         {"paragraph", "conflicts_with", "quote", "conflicting_quote", "message"})
        for concept in ("subject", "time", "conditions", "recommendations", "possibilities", "data"):
            self.assertIn(concept, system.lower())


if __name__ == "__main__":
    unittest.main()
