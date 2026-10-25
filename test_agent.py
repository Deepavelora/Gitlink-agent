import json
import unittest

from github_search import search_developers
from opportunity_search import search_opportunities
from cards import (
    create_card_message,
    build_search_form,
    build_opportunities_carousel,
    build_developers_carousel,
    build_opportunity_detail,
    build_developer_detail,
    build_candidate_application_form,
    build_review_application_card,
)
from main import parse_selection


class TestGitLinkAgent(unittest.TestCase):

    def test_opportunity_search_structure(self):
        """Verify search_opportunities returns valid structured opportunities."""
        results = search_opportunities(["python"], limit=3)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

        first = results[0]
        self.assertIn("id", first)
        self.assertIn("title", first)
        self.assertIn("company", first)
        self.assertIn("location", first)
        self.assertIn("url", first)
        self.assertIn("relevance_score", first)
        self.assertIsInstance(first["relevance_score"], int)

    def test_github_developer_search_structure(self):
        """Verify search_developers returns valid developer profiles."""
        results = search_developers(["python"], limit=3)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

        first = results[0]
        self.assertIn("id", first)
        self.assertIn("username", first)
        self.assertIn("top_repo", first)
        self.assertIn("language", first)
        self.assertIn("stars", first)
        self.assertIn("score", first)
        self.assertTrue(first["id"].startswith("dev_"))

    def test_search_form_card_payload(self):
        """Verify search form payload conforms to ASI:One form card specification."""
        form = build_search_form()
        self.assertEqual(form["title"], "GitLink Talent & Career Discovery")
        self.assertIn("fields", form)
        self.assertGreater(len(form["fields"]), 1)
        self.assertIn("submit_cta", form)
        self.assertEqual(form["submit_cta"]["selection"]["action"], "execute_search")

    def test_opportunities_carousel_card_payload(self):
        """Verify carousel card payload format and limits."""
        mock_opps = [
            {
                "id": "opp_test1",
                "title": "Senior Python Engineer",
                "company": "Stripe",
                "location": "Remote",
                "source": "Remotive",
                "salary": "$120,000",
                "relevance_score": 95,
            }
        ]
        carousel = build_opportunities_carousel(mock_opps, "python")
        self.assertEqual(carousel["title"], "Matched Developer Opportunities")
        self.assertEqual(len(carousel["items"]), 1)
        item = carousel["items"][0]
        self.assertEqual(item["id"], "opp_test1")
        self.assertEqual(item["primary_cta"]["selection"]["action"], "select_item")
        self.assertEqual(item["primary_cta"]["selection"]["item_id"], "opp_test1")

    def test_detail_card_payload(self):
        """Verify detail card has summary rows, sub-options, and CTAs."""
        mock_opp = {
            "id": "opp_test2",
            "title": "Agent Architect",
            "company": "Fetch AI",
            "location": "Remote",
            "source": "Fetch Network",
            "salary": "$140,000",
            "matched_terms": ["python", "agents"],
        }
        detail = build_opportunity_detail(mock_opp)
        self.assertIn("summary_rows", detail)
        self.assertIn("sub_options", detail)
        self.assertEqual(detail["sub_options"]["kind"], "radio")
        self.assertIn("ctas", detail)
        self.assertEqual(len(detail["ctas"]), 2)

    def test_candidate_application_form_payload(self):
        """Verify candidate application form captures all required applicant fields."""
        form = build_candidate_application_form("opp_test3", "Backend Engineer")
        field_names = [f["name"] for f in form["fields"]]
        self.assertIn("full_name", field_names)
        self.assertIn("email", field_names)
        self.assertIn("github_handle", field_names)
        self.assertIn("experience_level", field_names)
        self.assertEqual(form["submit_cta"]["selection"]["action"], "submit_application_form")

    def test_review_application_card_payload(self):
        """Verify review card schema has summary rows, approve_cta, and reject_cta."""
        candidate = {
            "full_name": "Sarah Connor",
            "email": "sarah@example.com",
            "github_handle": "sconnor",
            "experience_level": "senior",
            "pitch_highlight": "10 years building distributed AI agent clusters.",
        }
        review = build_review_application_card("AI Systems Lead", "Cyberdyne", candidate, "opp_test4")
        self.assertIn("summary_rows", review)
        self.assertIn("approve_cta", review)
        self.assertIn("reject_cta", review)
        self.assertEqual(review["approve_cta"]["selection"]["action"], "confirm_application")
        self.assertEqual(review["reject_cta"]["selection"]["action"], "cancel_application")

    def test_create_card_message_metadata(self):
        """Verify create_card_message properly constructs ChatMessage with metadata block."""
        carousel_payload = {"title": "Test Carousel", "items": []}
        msg = create_card_message("Test Narration", "carousel", carousel_payload)

        # Check content blocks
        self.assertEqual(len(msg.content), 2)
        text_block = msg.content[0]
        meta_block = msg.content[1]

        self.assertEqual(text_block.type, "text")
        self.assertEqual(text_block.text, "Test Narration")
        self.assertEqual(meta_block.type, "metadata")

        metadata = meta_block.metadata
        self.assertEqual(metadata["card_protocol_version"], "1")
        self.assertEqual(metadata["requires_card_interaction"], "true")
        self.assertEqual(metadata["card_kind"], "carousel")

        # Payload must be valid JSON string and under 64 KB limit
        payload_str = metadata["card_payload"]
        self.assertLessEqual(len(payload_str.encode("utf-8")), 64 * 1024)
        parsed = json.loads(payload_str)
        self.assertEqual(parsed["title"], "Test Carousel")

    def test_parse_selection_json(self):
        """Verify parse_selection correctly parses direct @mention JSON strings."""
        sample_json = json.dumps({"action": "select_item", "item_id": "opp_123", "item_type": "opportunity"})
        parsed = parse_selection(sample_json)
        self.assertEqual(parsed.get("action"), "select_item")
        self.assertEqual(parsed.get("item_id"), "opp_123")

    def test_parse_selection_prose_fallback(self):
        """Verify parse_selection correctly extracts actions and IDs from planner-mediated prose."""
        prose_msg = "The user confirmed the application for opp_789123."
        parsed = parse_selection(prose_msg)
        self.assertEqual(parsed.get("action"), "confirm_application")
        self.assertEqual(parsed.get("item_id"), "opp_789123")

        cancel_msg = "The user decided to cancel."
        self.assertEqual(parse_selection(cancel_msg).get("action"), "cancel_application")


if __name__ == "__main__":
    unittest.main()
