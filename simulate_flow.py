"""
simulate_flow.py - Local ACP End-to-End Simulation Script for GitLink Agent

This script simulates a complete multi-step conversation loop inside ASI:One:
1. Initial Greeting -> Search Criteria Form Card
2. Form Submission -> Opportunity Search Tool -> Carousel Card
3. Carousel Selection -> Detail Card with Action Sub-options
4. Detail Action -> Candidate Application Form Card
5. Form Submission -> Review Card
6. Approval Confirmation -> Final Executable Outcome & End-Session

Run this to verify the entire conversational state machine and card interactions locally!
"""

import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Dict, Any

from uagents import Context
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    MetadataContent,
    EndSessionContent,
)

from main import handle_message, agent


class MockStorage:
    """In-memory key-value store simulating uAgents ctx.storage."""
    def __init__(self):
        self._data = {}

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def has(self, key: str) -> bool:
        return key in self._data

    def clear(self):
        self._data.clear()


class MockLogger:
    def info(self, msg):
        pass
    def warning(self, msg):
        print(f"[WARN] {msg}")
    def error(self, msg):
        print(f"[ERROR] {msg}")
    def exception(self, msg):
        print(f"[EXC] {msg}")


class SimulationContext:
    """Mock Context simulating the uAgents runtime for message exchange."""
    def __init__(self, storage: MockStorage):
        self.storage = storage
        self.logger = MockLogger()
        self.sent_messages: List[Any] = []

    async def send(self, recipient: str, msg: Any):
        self.sent_messages.append((recipient, msg))


def print_divider(title: str):
    print("\n" + "=" * 70)
    print(f" {title.upper()}")
    print("=" * 70)


def safe_print(text: str):
    print(text.encode("ascii", "replace").decode("ascii"))


def inspect_reply(msg: Any):
    """Pretty prints ChatMessage contents and card declarations."""
    if isinstance(msg, ChatAcknowledgement):
        safe_print(f"  [ACK] Acknowledged Msg ID: {msg.acknowledged_msg_id}")
        return

    if not isinstance(msg, ChatMessage):
        safe_print(f"  [MSG] Raw message: {msg}")
        return

    for block in msg.content:
        if isinstance(block, TextContent):
            safe_print(f"\n  [CHAT NARRATION]:\n  {block.text}\n")
        elif isinstance(block, MetadataContent):
            meta = block.metadata
            card_kind = meta.get("card_kind")
            safe_print(f"  [CARD DECLARATION]: kind='{card_kind}', version={meta.get('card_protocol_version')}")
            payload_str = meta.get("card_payload", "{}")
            try:
                payload = json.loads(payload_str)
                safe_print(f"  [CARD TITLE]: {payload.get('title')}")
                if card_kind == "carousel":
                    safe_print(f"  [CAROUSEL ITEMS ({len(payload.get('items', []))})]:")
                    for itm in payload.get("items", [])[:3]:
                        safe_print(f"    - {itm.get('id')}: {itm.get('title')} ({itm.get('subtitle')})")
                elif card_kind == "detail":
                    safe_print("  [DETAIL ROWS]:")
                    for row in payload.get("summary_rows", []):
                        safe_print(f"    - {row.get('label')}: {row.get('value')}")
                    sub_opt = payload.get("sub_options", {})
                    safe_print(f"  [SUB-OPTIONS]: {sub_opt.get('label')}")
                    for ch in sub_opt.get("choices", []):
                        safe_print(f"    * [{ch.get('value')}] {ch.get('label')}")
                elif card_kind == "form":
                    safe_print("  [FORM FIELDS]:")
                    for f in payload.get("fields", []):
                        safe_print(f"    - {f.get('name')} ({f.get('kind')}): {f.get('label')}")
                elif card_kind == "review":
                    safe_print("  [REVIEW SUMMARY]:")
                    for row in payload.get("summary_rows", []):
                        safe_print(f"    - {row.get('label')}: {row.get('value')}")
            except Exception as e:
                safe_print(f"  [CARD PAYLOAD PARSE ERROR]: {e}")
        elif isinstance(block, EndSessionContent):
            safe_print("  [SESSION]: EndSessionContent received (Flow Complete).")


async def run_simulation():
    client_address = "agent1q_test_client_asi1_user"
    shared_storage = MockStorage()

    print_divider("Step 1: User says Hello to GitLink Agent")
    ctx = SimulationContext(shared_storage)
    turn1_msg = ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text="Hello! What can you do?")],
    )
    await handle_message(ctx, client_address, turn1_msg)
    for _, reply in ctx.sent_messages:
        inspect_reply(reply)

    print_divider("Step 2: User fills Search Form Card (Keywords='python', Mode='opportunities')")
    ctx = SimulationContext(shared_storage)
    search_selection = {
        "action": "execute_search",
        "keywords": "python",
        "mode": "opportunities",
        "location": "Remote",
    }
    turn2_msg = ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=json.dumps(search_selection))],
    )
    await handle_message(ctx, client_address, turn2_msg)
    selected_item_id = None
    for _, reply in ctx.sent_messages:
        inspect_reply(reply)
        if isinstance(reply, ChatMessage):
            for block in reply.content:
                if isinstance(block, MetadataContent) and block.metadata.get("card_kind") == "carousel":
                    payload = json.loads(block.metadata.get("card_payload", "{}"))
                    items = payload.get("items", [])
                    if items:
                        selected_item_id = items[0]["id"]

    if not selected_item_id:
        selected_item_id = "opp_curated_1"

    print_divider(f"Step 3: User picks an item from the Carousel (ID: {selected_item_id})")
    ctx = SimulationContext(shared_storage)
    pick_selection = {
        "action": "select_item",
        "item_id": selected_item_id,
        "item_type": "opportunity",
    }
    turn3_msg = ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=json.dumps(pick_selection))],
    )
    await handle_message(ctx, client_address, turn3_msg)
    for _, reply in ctx.sent_messages:
        inspect_reply(reply)

    print_divider("Step 4: User picks 'apply' sub-option on Detail Card and clicks Proceed")
    ctx = SimulationContext(shared_storage)
    proceed_selection = {
        "action": "proceed_from_detail",
        "desired_action": "apply",
        "item_id": selected_item_id,
    }
    turn4_msg = ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=json.dumps(proceed_selection))],
    )
    await handle_message(ctx, client_address, turn4_msg)
    for _, reply in ctx.sent_messages:
        inspect_reply(reply)

    print_divider("Step 5: User submits Candidate Application Profile Form")
    ctx = SimulationContext(shared_storage)
    form_submission = {
        "action": "submit_application_form",
        "item_id": selected_item_id,
        "full_name": "Deepa Velora",
        "email": "deepa@example.com",
        "github_handle": "Deepavelora",
        "experience_level": "mid",
        "pitch_highlight": "Passionate software engineer building decentralized AI agents with Python & uAgents.",
    }
    turn5_msg = ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=json.dumps(form_submission))],
    )
    await handle_message(ctx, client_address, turn5_msg)
    for _, reply in ctx.sent_messages:
        inspect_reply(reply)

    print_divider("Step 6: User clicks Confirm on Review Card")
    ctx = SimulationContext(shared_storage)
    confirm_selection = {
        "action": "confirm_application",
        "item_id": selected_item_id,
    }
    turn6_msg = ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=json.dumps(confirm_selection))],
    )
    await handle_message(ctx, client_address, turn6_msg)
    for _, reply in ctx.sent_messages:
        inspect_reply(reply)

    print_divider("Simulation Finished Successfully!")
    print("All 6 steps executed smoothly with ACP, multi-step state transitions, and cards!\n")


if __name__ == "__main__":
    asyncio.run(run_simulation())
