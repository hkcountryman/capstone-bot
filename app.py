"""A Flask server for the WhatsApp chatbot.

This module handles the route to make requests to the bot.
"""
import os
from typing import List, Tuple

from flask import Flask, Request, request

from chatbot import Chatbot

app = Flask(__name__)
"""The server running the chatbot."""


def get_incoming_msg(req: Request) -> Tuple[str, str, str, List[str]]:
    """Get an incoming message sent to the bot and its sender.

    Arguments:
        req -- Flask Request object

    Returns:
        The message contents, sender contact info, sender name, and media URLs
            from a POST request to the bot.
    """
    msg: str = req.values.get(
        "Body",
        default="Hello, world",
        type=str).strip()  # type: ignore [union-attr]
    sender_contact: str = req.values.get(
        "From", type=str)  # type: ignore [assignment]
    sender_name: str = req.values.get(
        "ProfileName", type=str)  # type: ignore [assignment]
    media_urls = [req.values[k]
                  for k in req.values.keys() if k.startswith("MediaUrl")]

    return (msg, sender_contact, sender_name, media_urls)


TWILIO_ACCOUNT_SID: str = os.getenv(
    "TWILIO_ACCOUNT_SID")  # type: ignore [assignment]
TWILIO_AUTH_TOKEN: str = os.getenv(
    "TWILIO_AUTH_TOKEN")  # type: ignore [assignment]
TWILIO_NUMBER: str = os.getenv("TWILIO_NUMBER")  # type: ignore [assignment]
SUBSCRIBER_FILE: str = "bot_subscribers/team56test.json"
mr_botty = Chatbot(
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_NUMBER,
    SUBSCRIBER_FILE)
"""Global Chatbot object, of which there could theoretically be many."""


@app.route("/bot", methods=["POST"])
# TODO: theoretically we could support multiple bots on one server, but
# they'd each need their own routing. Use case for blueprints? Might also
# want to try the routes as keys in a dictionary containing Chatbot objects.
def bot() -> str:
    """Bot's response to a request.

    Returns:
        The bot's response.
    """
    (msg, sender_contact, sender_name, media_urls) = get_incoming_msg(request)

    return mr_botty.process_msg(
        msg,
        sender_contact,
        sender_name,
        media_urls)
