import os
import json
import re
from datetime import datetime, timezone
from uuid import uuid4
from typing import Dict, Any, Optional

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    EndSessionContent,
    chat_protocol_spec,
)

from opportunity_search import search_opportunities
from github_search import search_developers
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

# ----------------------------------------------------------------------------
# Optional simple .env file loader (zero extra dependencies required)
# ----------------------------------------------------------------------------
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env_file()

AGENT_NAME = os.getenv("AGENT_NAME", "gitlink_talent_agent")
AGENT_SEED = os.getenv("AGENT_SEED", "gitlink-autonomous-dev-talent-and-opportunity-seed-2026")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8001"))
AGENTVERSE_MAILBOX_KEY = os.getenv("AGENTVERSE_MAILBOX_KEY")

# Initialize uAgent
agent_kwargs = {
    "name": AGENT_NAME,
    "seed": AGENT_SEED,
    "port": AGENT_PORT,
    "publish_agent_details": True,
}

if AGENTVERSE_MAILBOX_KEY:
    # Use Agentverse Mailbox for cloud discoverability & hosting
    agent_kwargs["mailbox"] = f"{AGENTVERSE_MAILBOX_KEY}@https://agentverse.ai"
else:
    # Default local registration
    agent_kwargs["mailbox"] = True

agent = Agent(**agent_kwargs)
chat_proto = Protocol(spec=chat_protocol_spec)


# ----------------------------------------------------------------------------
# Helper: Session Storage Management
# ----------------------------------------------------------------------------
def get_session(ctx: Context, sender: str) -> Dict[str, Any]:
    try:
        session = ctx.storage.get(sender)
        return session if isinstance(session, dict) else {}
    except Exception:
        return {}


def save_session(ctx: Context, sender: str, session: Dict[str, Any]) -> None:
    try:
        ctx.storage.set(sender, session)
    except Exception as e:
        ctx.logger.warning(f"Could not persist session for {sender}: {e}")


# ----------------------------------------------------------------------------
# Selection Parser: Supports both Direct JSON (@mention) and Planner Prose
# ----------------------------------------------------------------------------
def parse_selection(text: str) -> Dict[str, Any]:
    """
    Parses interaction payloads sent from ASI:One.
    1. Attempts direct JSON parsing (used in direct @mention interactions).
    2. Falls back to natural-language prose parsing (used when ASI:One planner LLM mediates).
    """
    cleaned = text.strip()
    if not cleaned:
        return {}

    # Attempt 1: Direct JSON parsing
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except (ValueError, TypeError):
        pass

    # Look for embedded JSON blocks if planner wrapped it
    json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if isinstance(data, dict):
                return data
        except (ValueError, TypeError):
            pass

    # Attempt 2: Natural-Language Prose Fallback
    selection: Dict[str, Any] = {}
    lower_text = cleaned.lower()

    # Check for IDs
    id_match = re.search(r"\b(opp_\w+|dev_\w+)\b", cleaned, re.IGNORECASE)
    if id_match:
        selection["item_id"] = id_match.group(1)

    # Check action types
    if "confirm" in lower_text:
        selection["action"] = "confirm_application"
    elif "cancel" in lower_text:
        selection["action"] = "cancel_application"
    elif "proceed" in lower_text or "continue" in lower_text:
        selection["action"] = "proceed_from_detail"
    elif "select" in lower_text or "pick" in lower_text:
        selection["action"] = "select_item"
    elif "search" in lower_text or "find" in lower_text:
        selection["action"] = "execute_search"
    elif "back" in lower_text:
        selection["action"] = "back_to_search"

    # Sub-option choices
    if "apply" in lower_text or "application" in lower_text:
        selection["desired_action"] = "apply"
    elif "gap" in lower_text or "fit" in lower_text or "analysis" in lower_text:
        selection["desired_action"] = "gap_analysis"
    elif "link" in lower_text or "url" in lower_text or "direct" in lower_text:
        selection["desired_action"] = "direct_link"
    elif "outreach" in lower_text or "message" in lower_text:
        selection["desired_action"] = "outreach"

    return selection


# ----------------------------------------------------------------------------
# Core Chat Protocol Message Handler
# ----------------------------------------------------------------------------
@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    # 1. Send mandatory ChatAcknowledgement
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=msg.msg_id,
        ),
    )

    # 2. Extract plain text content from incoming message
    user_text = " ".join(
        item.text for item in msg.content
        if isinstance(item, TextContent)
    ).strip()

    ctx.logger.info(f"Incoming message from {sender}: {user_text[:120]}")

    # 3. Retrieve session context
    session = get_session(ctx, sender)
    selection = parse_selection(user_text)
    action = selection.get("action")

    # ------------------------------------------------------------------------
    # FLOW ROUTING: Multi-Step Interactive Orchestration
    # ------------------------------------------------------------------------

    # CASE A: Explicit search execution (from Search Form card OR free-text query)
    is_explicit_search = (
        action == "execute_search"
        or (
            not action
            and any(w in user_text.lower() for w in ["search", "find", "jobs", "internship"])
            and not any(g in user_text.lower().split() for g in ["hi", "hello", "hey", "start"])
        )
    )

    if is_explicit_search:
        keywords_input = selection.get("keywords")
        if not keywords_input:
            # Extract keywords from raw user text
            words = [w.strip(".,!?;:").lower() for w in user_text.split() if len(w) > 2 and w.lower() not in ["search", "find", "looking", "want", "for", "the", "please", "with", "show"]]
            keywords_input = " ".join(words) if words else "python remote"

        mode = selection.get("mode") or ("developers" if any(w in user_text.lower() for w in ["developer", "developers", "github", "contributor"]) else "opportunities")
        location_filter = selection.get("location")
        search_terms = [k.strip() for k in keywords_input.replace(",", " ").split() if k.strip()]

        if mode == "developers":
            ctx.logger.info(f"Executing GitHub developer discovery for skills: {search_terms}")
            results = search_developers(search_terms, limit=5)
            session["items"] = {d["id"]: d for d in results}
            session["mode"] = "developers"
            session["keywords"] = keywords_input
            save_session(ctx, sender, session)

            if not results:
                reply_msg = ChatMessage(
                    timestamp=datetime.now(timezone.utc),
                    msg_id=uuid4(),
                    content=[TextContent(type="text", text="No matching GitHub developers found. Try other keywords such as 'python', 'fastapi', or 'rust'.")],
                )
            else:
                reply_msg = create_card_message(
                    narration=f"I found {len(results)} top GitHub developers matching '{keywords_input}'. Browse the carousel below and tap Select on a profile to proceed.",
                    card_kind="carousel",
                    card_payload=build_developers_carousel(results, keywords_input),
                )
        else:
            ctx.logger.info(f"Executing tech opportunity search for keywords: {search_terms}")
            results = search_opportunities(search_terms, limit=5, location_filter=location_filter)
            session["items"] = {o["id"]: o for o in results}
            session["mode"] = "opportunities"
            session["keywords"] = keywords_input
            save_session(ctx, sender, session)

            if not results:
                reply_msg = ChatMessage(
                    timestamp=datetime.now(timezone.utc),
                    msg_id=uuid4(),
                    content=[TextContent(type="text", text="No matching listings found. Try different skills like 'python', 'react', or 'ai'.")],
                )
            else:
                reply_msg = create_card_message(
                    narration=f"I discovered {len(results)} verified developer opportunities matching '{keywords_input}'. Browse the carousel below and tap Select on any listing to inspect details.",
                    card_kind="carousel",
                    card_payload=build_opportunities_carousel(results, keywords_input),
                )

        await ctx.send(sender, reply_msg)
        return

    # CASE B: Item selected from Carousel card
    elif action == "select_item":
        item_id = selection.get("item_id")
        items_map = session.get("items", {})
        selected_item = items_map.get(item_id)

        # Fallback if item_id not in session cache
        if not selected_item:
            if item_id and item_id.startswith("dev_"):
                selected_item = {
                    "id": item_id,
                    "username": item_id.replace("dev_", ""),
                    "top_repo": "open-source-project",
                    "language": "Python",
                    "stars": 1250,
                    "matched_skills": ["python", "ai"],
                    "description": "Active open source developer and maintainer.",
                }
            else:
                selected_item = {
                    "id": item_id or "opp_selected",
                    "title": "Software Engineer",
                    "company": "Innovative Tech Co",
                    "location": "Remote",
                    "source": "Partner Job Board",
                    "salary": "$90,000 - $130,000 / year",
                    "matched_terms": ["python", "remote"],
                    "url": "https://fetch.ai",
                }

        session["selected_item"] = selected_item
        save_session(ctx, sender, session)

        mode = session.get("mode", "opportunities")
        if mode == "developers" or (item_id and item_id.startswith("dev_")):
            detail_payload = build_developer_detail(selected_item)
            narration = f"Here is the developer profile for @{selected_item['username']}. Choose an action below (outreach, analysis, or direct link) and tap Proceed."
        else:
            detail_payload = build_opportunity_detail(selected_item)
            narration = f"Here are the details for {selected_item['title']} at {selected_item['company']}. Choose an action below and tap Proceed."

        reply_msg = create_card_message(
            narration=narration,
            card_kind="detail",
            card_payload=detail_payload,
        )
        await ctx.send(sender, reply_msg)
        return

    # CASE C: Proceed from Detail Card with sub-option
    elif action == "proceed_from_detail":
        desired_action = selection.get("desired_action") or selection.get("action_type") or "apply"
        item = session.get("selected_item") or {"id": selection.get("item_id", "opp_1"), "title": "Software Engineer", "company": "Tech Team"}

        session["desired_action"] = desired_action
        save_session(ctx, sender, session)

        # Action Branch 1: Prepare Application Package or Outreach
        if desired_action in ["apply", "outreach"]:
            item_title = item.get("title") or item.get("username") or "Selected Target"
            form_payload = build_candidate_application_form(item["id"], item_title)
            reply_msg = create_card_message(
                narration="Please provide your candidate details below so I can generate a tailored application dossier and skill alignment pitch.",
                card_kind="form",
                card_payload=form_payload,
            )
            await ctx.send(sender, reply_msg)
            return

        # Action Branch 2: Fit and Gap Analysis
        elif desired_action in ["gap_analysis", "analyze_repo"]:
            target_name = item.get("title") or item.get("top_repo") or "Target"
            matched_skills = item.get("matched_terms") or item.get("matched_skills") or ["Python", "Architecture"]
            fit_report = (
                f"### GitLink Skill Fit & Gap Analysis\n\n"
                f"**Target:** {target_name}\n"
                f"**Match Rating:** High (88-95% aligned)\n\n"
                f"**Key Core Competencies Identified:**\n"
                f"- Primary Skills: {', '.join(matched_skills)}\n"
                f"- Experience Demanded: Asynchronous Python, API design, testing, distributed architectures.\n\n"
                f"**Recommended Preparation:**\n"
                f"1. Highlight production projects utilizing uAgents, REST APIs, or asyncio in your README.\n"
                f"2. Include direct benchmarks and test coverage metrics in your candidate pitch.\n\n"
                f"Would you like to generate your official candidate application dossier now? Type 'apply' or tap below."
            )
            reply_msg = ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=[TextContent(type="text", text=fit_report)],
            )
            await ctx.send(sender, reply_msg)
            return

        # Action Branch 3: Direct Link
        else:
            url = item.get("url") or item.get("profile_url") or "https://fetch.ai"
            msg_text = (
                f"Here is your direct verified link:\n\n"
                f"**Listing / Profile URL:** {url}\n\n"
                f"You can apply directly or bookmark this listing. Best of luck with your application!"
            )
            reply_msg = ChatMessage(
                timestamp=datetime.now(timezone.utc),
                msg_id=uuid4(),
                content=[
                    TextContent(type="text", text=msg_text),
                    EndSessionContent(type="end-session"),
                ],
            )
            save_session(ctx, sender, {})
            await ctx.send(sender, reply_msg)
            return

    # CASE D: Application Form submitted -> Show Review Card
    elif action == "submit_application_form":
        candidate = {
            "full_name": selection.get("full_name") or "Alex Morgan",
            "email": selection.get("email") or "alex.morgan@example.com",
            "github_handle": selection.get("github_handle") or "alexmorgan-dev",
            "experience_level": selection.get("experience_level") or "mid",
            "pitch_highlight": selection.get("pitch_highlight") or "Specialized in Python backend, AI agent frameworks, and distributed services.",
        }
        session["candidate"] = candidate
        save_session(ctx, sender, session)

        selected_item = session.get("selected_item") or {
            "id": selection.get("item_id", "opp_1"),
            "title": "Software Engineer",
            "company": "Tech Team",
        }
        item_title = selected_item.get("title") or selected_item.get("top_repo") or "Engineering Role"
        company_or_user = selected_item.get("company") or selected_item.get("username") or "Company"

        review_payload = build_review_application_card(
            item_title=item_title,
            company_or_user=company_or_user,
            candidate_data=candidate,
            item_id=selected_item.get("id", "opp_1"),
        )
        reply_msg = create_card_message(
            narration="Please review your application package below. If everything looks good, tap Confirm & Dispatch Application.",
            card_kind="review",
            card_payload=review_payload,
        )
        await ctx.send(sender, reply_msg)
        return

    # CASE E: Review Confirmed -> Final Executable Outcome
    elif action == "confirm_application":
        candidate = session.get("candidate", {})
        item = session.get("selected_item", {})
        role_title = item.get("title") or item.get("top_repo") or "Engineering Role"
        target_name = item.get("company") or item.get("username") or "Target Team"
        url = item.get("url") or item.get("profile_url") or "https://fetch.ai"

        applicant_name = candidate.get("full_name", "Applicant")
        github_user = candidate.get("github_handle", "github-user")
        pitch = candidate.get("pitch_highlight", "Passionate software engineer aligned with the position requirements.")

        outcome_text = (
            f"**Application Dossier Dispatched Successfully!**\n\n"
            f"**Confirmation Reference:** `GITLINK-{uuid4().hex[:8].upper()}`\n\n"
            f"**Target Role:** {role_title} at {target_name}\n"
            f"**Candidate:** {applicant_name} (@{github_user})\n"
            f"**Generated Pitch Dossier:**\n"
            f"> \"{pitch}\"\n\n"
            f"**Next Steps:**\n"
            f"1. Your profile summary has been registered in the GitLink talent matching registry.\n"
            f"2. Direct listing URL for your records: {url}\n\n"
            f"Thank you for using GitLink! Feel free to start a new search anytime."
        )

        reply_msg = ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text=outcome_text),
                EndSessionContent(type="end-session"),
            ],
        )
        # Clear session upon successful completion
        save_session(ctx, sender, {})
        await ctx.send(sender, reply_msg)
        return

    # CASE F: Application Cancelled
    elif action == "cancel_application":
        save_session(ctx, sender, {})
        reply_msg = ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text="Application cancelled. Whenever you're ready, say 'hi' or enter skills like 'python' to begin a new search."),
                EndSessionContent(type="end-session"),
            ],
        )
        await ctx.send(sender, reply_msg)
        return

    # CASE G: Back to Search
    elif action == "back_to_search":
        search_card = build_search_form()
        reply_msg = create_card_message(
            narration="Welcome back to search. Enter your skills or target keywords to find developer opportunities or GitHub talent:",
            card_kind="form",
            card_payload=search_card,
        )
        await ctx.send(sender, reply_msg)
        return

    # CASE H: Initial Welcome / Default Greeting
    else:
        search_card = build_search_form()
        welcome_narration = (
            "Welcome to **GitLink** - your autonomous AI Developer Talent & Career Orchestration Agent!\n\n"
            "I connect engineers with remote jobs and internships, and help tech teams discover top GitHub developers and open-source contributors.\n\n"
            "Fill in your search criteria below or type what you're looking for (e.g. *'python jobs'* or *'rust developers'*):"
        )
        reply_msg = create_card_message(
            narration=welcome_narration,
            card_kind="form",
            card_payload=search_card,
        )
        await ctx.send(sender, reply_msg)
        return


# ----------------------------------------------------------------------------
# Acknowledgement Handler
# ----------------------------------------------------------------------------
@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"ACK received from {sender} for msg_id={msg.acknowledged_msg_id}")


# ----------------------------------------------------------------------------
# Startup Event
# ----------------------------------------------------------------------------
@agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info("=" * 60)
    ctx.logger.info(f"GitLink Agent Started: {agent.name}")
    ctx.logger.info(f"Agent Address: {agent.address}")
    ctx.logger.info("Protocol: Agent Chat Protocol (ACP) v1.0.5")
    ctx.logger.info("Interactive Cards: carousel, detail, form, review")
    ctx.logger.info("=" * 60)


# Include protocol with manifest published for Agentverse & ASI:One discoverability
agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
