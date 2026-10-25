import json
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Dict, Any, Optional

from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    TextContent,
    MetadataContent,
)


def create_card_message(
    narration: str,
    card_kind: str,
    card_payload: Dict[str, Any],
    is_terminal: bool = False,
    drawer_width: str = "540",
) -> ChatMessage:
    """
    Build a compliant ChatMessage with one TextContent block and one MetadataContent block
    declaring an ASI:One Interactive Card according to the ACP card specification.
    """
    metadata = {
        "card_protocol_version": "1",
        "requires_card_interaction": "false" if is_terminal else "true",
        "card_kind": card_kind,
        "card_payload": json.dumps(card_payload),
        "preferred_drawer_width_px": str(drawer_width),
    }

    if is_terminal:
        metadata["is_terminal"] = "true"

    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[
            TextContent(type="text", text=narration),
            MetadataContent(type="metadata", metadata=metadata),
        ],
    )


def build_search_form() -> Dict[str, Any]:
    """Form card to configure talent or opportunity search criteria."""
    return {
        "title": "GitLink Talent & Career Discovery",
        "fields": [
            {
                "name": "keywords",
                "kind": "text",
                "label": "Skills / Tech Stack",
                "required": True,
                "placeholder": "e.g. python, fastapi, react, rust, ai",
            },
            {
                "name": "mode",
                "kind": "select",
                "label": "What are you searching for?",
                "options": [
                    {"value": "opportunities", "label": "Jobs & Internships (Remotive + Arbeitnow)"},
                    {"value": "developers", "label": "GitHub Developers & Open-Source Projects"},
                ],
            },
            {
                "name": "location",
                "kind": "text",
                "label": "Location Preference (optional)",
                "placeholder": "e.g. Remote, Worldwide, Europe, US",
            },
        ],
        "submit_cta": {
            "label": "Find Matches",
            "selection": {"action": "execute_search"},
        },
    }


def build_opportunities_carousel(opportunities: List[Dict[str, Any]], keywords: str) -> Dict[str, Any]:
    """Carousel card displaying matching tech jobs/internships."""
    items = []
    for opp in opportunities[:6]:
        score = opp.get("relevance_score", 85)
        badge_variant = "success" if score >= 90 else "info"

        items.append({
            "id": opp["id"],
            "image": "https://raw.githubusercontent.com/fetchai/uAgents/main/docs/static/img/uagents-logo.png",
            "title": opp["title"][:50],
            "subtitle": f"{opp['company']} · {opp['location']}",
            "badges": [
                {"label": f"{score}% Match", "variant": badge_variant},
                {"label": opp["source"], "variant": "info"},
            ],
            "secondary_text": opp.get("salary", "Disclosed on Application"),
            "primary_cta": {
                "label": "Select",
                "selection": {
                    "action": "select_item",
                    "item_id": opp["id"],
                    "item_type": "opportunity",
                },
            },
        })

    return {
        "title": "Matched Developer Opportunities",
        "subtitle": f"Top listings for: {keywords}",
        "items": items,
    }


def build_developers_carousel(developers: List[Dict[str, Any]], keywords: str) -> Dict[str, Any]:
    """Carousel card displaying matching GitHub developers/repositories."""
    items = []
    for dev in developers[:6]:
        score = dev.get("score", 80)
        badge_variant = "success" if score >= 90 else "info"

        items.append({
            "id": dev["id"],
            "image": dev.get("avatar_url") or "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
            "title": dev["username"],
            "subtitle": f"Top Project: {dev['top_repo']} ({dev['language']})",
            "badges": [
                {"label": f"{score}% Fit", "variant": badge_variant},
                {"label": f"★ {dev['stars']}", "variant": "warning"},
            ],
            "secondary_text": f"Skills: {', '.join(dev.get('matched_skills', [])[:3])}",
            "primary_cta": {
                "label": "Select",
                "selection": {
                    "action": "select_item",
                    "item_id": dev["id"],
                    "item_type": "developer",
                },
            },
        })

    return {
        "title": "Top GitHub Developers & Repositories",
        "subtitle": f"Specialists matching: {keywords}",
        "items": items,
    }


def build_opportunity_detail(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Detail card for a single job opportunity with action selector."""
    matched_skills = ", ".join(opp.get("matched_terms", ["Software Engineering"]))

    return {
        "title": f"{opp['title']} · {opp['company']}",
        "hero_image": "https://raw.githubusercontent.com/fetchai/uAgents/main/docs/static/img/uagents-logo.png",
        "summary_rows": [
            {"label": "Company", "value": opp["company"]},
            {"label": "Location", "value": opp["location"]},
            {"label": "Source", "value": opp["source"]},
            {"label": "Compensation", "value": opp.get("salary", "Disclosed on Application")},
            {"label": "Matched Tech", "value": matched_skills},
        ],
        "sub_options": {
            "name": "desired_action",
            "kind": "radio",
            "label": "Next Step",
            "choices": [
                {
                    "value": "apply",
                    "label": "Prepare Candidate Application Package",
                    "secondary_text": "Draft profile dossier, pitch note & portfolio match",
                },
                {
                    "value": "gap_analysis",
                    "label": "Analyze Skill Gap & Recommendations",
                    "secondary_text": "View breakdown of strengths and requirements",
                },
                {
                    "value": "direct_link",
                    "label": "Direct Career Portal Link",
                    "secondary_text": "Retrieve full URL and external application guidance",
                },
            ],
        },
        "ctas": [
            {
                "label": "Proceed",
                "primary": True,
                "selection": {
                    "action": "proceed_from_detail",
                    "item_id": opp["id"],
                    "item_type": "opportunity",
                },
            },
            {
                "label": "Back to Search",
                "selection": {"action": "back_to_search"},
            },
        ],
    }


def build_developer_detail(dev: Dict[str, Any]) -> Dict[str, Any]:
    """Detail card for a single GitHub developer with action selector."""
    return {
        "title": f"Developer Profile: {dev['username']}",
        "hero_image": dev.get("avatar_url") or "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
        "summary_rows": [
            {"label": "GitHub Handle", "value": f"@{dev['username']}"},
            {"label": "Top Repository", "value": dev["top_repo"]},
            {"label": "Primary Language", "value": dev["language"]},
            {"label": "Total Stars", "value": str(dev["stars"])},
            {"label": "Key Skills", "value": ", ".join(dev.get("matched_skills", []))},
        ],
        "sub_options": {
            "name": "desired_action",
            "kind": "radio",
            "label": "Next Step",
            "choices": [
                {
                    "value": "outreach",
                    "label": "Generate Recruiter Outreach Message",
                    "secondary_text": "Personalized message referencing their open-source contributions",
                },
                {
                    "value": "analyze_repo",
                    "label": "Repository Deep Dive",
                    "secondary_text": "Inspect architecture, license, and community velocity",
                },
                {
                    "value": "view_profile",
                    "label": "Direct GitHub Profile URL",
                    "secondary_text": "Open official GitHub link",
                },
            ],
        },
        "ctas": [
            {
                "label": "Proceed",
                "primary": True,
                "selection": {
                    "action": "proceed_from_detail",
                    "item_id": dev["id"],
                    "item_type": "developer",
                },
            },
            {
                "label": "Back to Search",
                "selection": {"action": "back_to_search"},
            },
        ],
    }


def build_candidate_application_form(item_id: str, item_title: str) -> Dict[str, Any]:
    """Form card to gather candidate details for role application or talent outreach."""
    return {
        "title": f"Applicant Profile: {item_title[:40]}",
        "fields": [
            {
                "name": "full_name",
                "kind": "text",
                "label": "Full Name",
                "required": True,
                "placeholder": "e.g. Alex Morgan",
            },
            {
                "name": "email",
                "kind": "email",
                "label": "Email Address",
                "required": True,
                "placeholder": "e.g. alex.morgan@example.com",
            },
            {
                "name": "github_handle",
                "kind": "text",
                "label": "GitHub Profile Username",
                "required": True,
                "placeholder": "e.g. alexmorgan-dev",
            },
            {
                "name": "experience_level",
                "kind": "select",
                "label": "Experience Level",
                "options": [
                    {"value": "intern", "label": "Student / Aspiring Intern"},
                    {"value": "junior", "label": "Junior Engineer (1-2 years)"},
                    {"value": "mid", "label": "Mid-Level Engineer (3-5 years)"},
                    {"value": "senior", "label": "Senior Engineer / Tech Lead (5+ years)"},
                ],
            },
            {
                "name": "pitch_highlight",
                "kind": "text",
                "label": "Key Strengths / Elevator Pitch",
                "placeholder": "e.g. Passionate about autonomous agents, Python backends, and open source.",
            },
        ],
        "submit_cta": {
            "label": "Review Application Package",
            "selection": {
                "action": "submit_application_form",
                "item_id": item_id,
            },
        },
    }


def build_review_application_card(
    item_title: str,
    company_or_user: str,
    candidate_data: Dict[str, Any],
    item_id: str,
) -> Dict[str, Any]:
    """Review card to review and confirm the submitted dossier before completion."""
    exp_labels = {
        "intern": "Student / Aspiring Intern",
        "junior": "Junior Engineer (1-2 years)",
        "mid": "Mid-Level Engineer (3-5 years)",
        "senior": "Senior Engineer / Tech Lead (5+ years)",
    }
    exp_display = exp_labels.get(candidate_data.get("experience_level", ""), candidate_data.get("experience_level", "Mid-Level"))

    return {
        "title": "Review & Confirm Application Dossier",
        "summary_rows": [
            {"label": "Target Role / Dev", "value": f"{item_title} ({company_or_user})"},
            {"label": "Candidate Name", "value": candidate_data.get("full_name", "Applicant")},
            {"label": "Email", "value": candidate_data.get("email", "N/A")},
            {"label": "GitHub Handle", "value": f"@{candidate_data.get('github_handle', 'anonymous')}"},
            {"label": "Experience", "value": exp_display},
            {"label": "Pitch", "value": candidate_data.get("pitch_highlight", "Tailored fit for target role")[:80]},
        ],
        "approve_cta": {
            "label": "Confirm & Dispatch Application",
            "primary": True,
            "selection": {
                "action": "confirm_application",
                "item_id": item_id,
            },
        },
        "reject_cta": {
            "label": "Cancel",
            "selection": {
                "action": "cancel_application",
                "item_id": item_id,
            },
        },
    }
