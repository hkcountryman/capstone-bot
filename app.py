"""A Flask server for the WhatsApp chatbot.

This module handles the route to make requests to the bot.

Functions:
    bot -- The function that responds to a message sent to a chatbot (to support
        another group chat, another bot would have to be created with its own
        endpoint function and its own Twilio number)
"""
import html
from typing import List, Tuple

from flask import Flask, Request, request

from chatbot import mr_botty

app = Flask(__name__)
"""The server running the chatbot."""


def _get_incoming_msg(req: Request) -> Tuple[str, str, List[str]]:
    """Get an incoming message sent to the bot and its sender.

    Arguments:
        req -- Flask Request object

    Returns:
        The message contents, sender contact info, sender name, and media URLs
            from a POST request to the bot.
    """
    msg: str = html.escape(req.values.get(
        "Body",
        default="Hello, world",
        type=str).strip())  # type: ignore [union-attr]
    sender_contact: str = html.escape(req.values.get(
        "From", type=str))  # type: ignore [union-attr,assignment,type-var]
    media_urls = [req.values[k]
                  for k in req.values.keys() if k.startswith("MediaUrl")]
    return (msg, sender_contact, media_urls)


# Theoretically we could support multiple bots on one server, but they'd
# each need their own routing.
@app.route("/bot", methods=["POST"])
def bot() -> str:
    """Bot's response to a request.

    Returns:
        The bot's response.
    """
    (msg, sender_contact, media_urls) = _get_incoming_msg(request)
    return mr_botty.process_msg(
        msg,
        sender_contact,
        media_urls)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
