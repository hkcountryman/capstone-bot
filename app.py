"""A Flask server for the WhatsApp chatbot.

This module handles the route to make requests to the bot.
"""

from typing import Tuple

from flask import Flask, Request, request

from chatbot import mr_botty

app = Flask(__name__)
"""The server running the chatbot."""


def get_incoming_msg(req: Request) -> Tuple[str, str, str]:
    """Get an incoming message sent to the bot and its sender.

    Arguments:
        req -- Flask Request object

    Returns:
        The message contents from a POST request to the bot as well as the
            sender contact info and name.
    """
    msg: str = req.values.get(
        "Body",
        default="Hello, world",
        type=str).strip()  # type: ignore [union-attr]
    sender_contact: str = request.values.get(
        "From", type=str)  # type: ignore [assignment]
    sender_name: str = request.values.get(
        "ProfileName", type=str)  # type: ignore [assignment]
    return (msg, sender_contact, sender_name)


# TODO: theoretically we could support multiple bots on one server, but
# they'd each need their own routing. Use case for blueprints? Might also
# want to try the routes as keys in a dictionary containing Chatbot objects.
@app.route("/bot", methods=["POST"])
def bot() -> str:
    """Bot's response to a request.

    Returns:
        The bot's response.
    """
    # Test: texting me and my mom a message :) it works!
    # mr_botty.push("This is a push message from Halle. Hi!", [
    #               "+15106485015", "+15104104268"])
    (msg, sender_contact, sender_name) = get_incoming_msg(request)
    # # TODO: return mr_botty.process_msg(msg, sender_contact, sender_name)
    # return mr_botty.reply('You said: "' + msg + '"')
    translated_msg = mr_botty.translate_to(msg, "es")
    response = mr_botty.reply(
        f'You said: "{msg}". Translated to Spanish: "{translated_msg}"')
    return response
