from pathlib import Path
import unittest

from rfr_markdown import paragraph_range, read_paragraphs


FIXTURE = (Path(__file__).resolve().parents[1] / "test-statements.md").read_text()


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


if __name__ == "__main__":
    unittest.main()
