
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    EndSessionContent,
    chat_protocol_spec,
)

from opportunity_search import search_opportunities

agent = Agent(
    name="gitlink_opportunity_agent",
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
        item.text for item in msg.content
        if isinstance(item, TextContent)
    )

    keywords = [
        word.strip(".,!?;:").lower()
        for word in user_text.split()
        if len(word.strip(".,!?;:")) > 2
    ]

    if not keywords:
        reply = (
            "Tell me what you're looking for, such as "
            "'Python internship' or 'remote data analyst job'."
        )
    else:
        try:
            results = search_opportunities(keywords, limit=5)

            if not results:
                reply = (
                    "I couldn't find matching listings in the "
                    "available sources. Try different keywords."
                )
            else:
                lines = ["Here are opportunities matching your request:"]
                for i, job in enumerate(results, start=1):
                    lines.append(
                        f"\n{i}. {job['title']}\n"
                        f"Company: {job['company']}\n"
                        f"Location: {job['location']}\n"
                        f"Source: {job['source']}\n"
                        f"Matched keywords: "
                        f"{', '.join(job['matched_terms'])}\n"
                        f"Link: {job['url']}\n"
                        "Please check the original listing for "
                        "eligibility and deadline."
                    )
                reply = "\n".join(lines)[:10000]
        except Exception:
            ctx.logger.exception("Opportunity search failed")
            reply = "Opportunity search failed. Please try again."

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


