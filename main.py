
import io
from contextlib import redirect_stdout

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    EndSessionContent,
    chat_protocol_spec,
)

from github_search import search_developers


agent = Agent(
    name="gitlink_developer_discovery",
    seed="gitlink-local-demo-change-this-seed-before-deployment",
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)

chat_proto = Protocol(spec=chat_protocol_spec)


@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(acknowledged_msg_id=msg.msg_id),
    )

    user_text = " ".join(
        item.text
        for item in msg.content
        if isinstance(item, TextContent)
    )

    skills = [
        skill for skill in [
            "python", "fastapi", "machine learning",
            "java", "sql", "react", "docker",
            "kubernetes", "django", "flask",
        ]
        if skill in user_text.lower()
    ]

    if not skills:
        reply = (
            "Tell me which skills you need. For example: "
            "Find Python developers with FastAPI experience."
        )
    else:
        try:
            output = io.StringIO()
            with redirect_stdout(output):
                search_developers(skills, limit=10)

            results = output.getvalue().strip()
            reply = results[:10000] if results else (
                "No matching repositories found. Try other skills."
            )
        except Exception:
            ctx.logger.exception("GitHub search failed")
            reply = "GitHub search failed. Please try again."

    await ctx.send(
        sender,
        ChatMessage(
            content=[
                TextContent(type="text", text=reply),
                EndSessionContent(type="end-session"),
            ]
        ),
    )


@chat_proto.on_message(ChatAcknowledgement)
async def handle_ack(
    ctx: Context, sender: str, msg: ChatAcknowledgement
):
    ctx.logger.info("Chat acknowledgement received")


agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    agent.run()

@chat_proto.on_message(ChatAcknowledgement)
async def handle_acknowledgement(
    ctx: Context, sender: str, msg: ChatAcknowledgement
):
    ctx.logger.info("Received chat acknowledgement from %s", sender)