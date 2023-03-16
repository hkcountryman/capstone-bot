"""A Flask server for the WhatsApp chatbot.

This module handles the route to make requests to the bot.
"""

from typing import Tuple

from flask import Flask, Request, request

from chatbot import Chatbot, mr_botty

app = Flask(__name__)
"""The server running the chatbot."""


# TODO: functions to determine whether message is message to the group or a
# bot command. May use switch case to parse first word of message once
# trimmed of leading whitespace. I'm thinking
#
# See match case in Chatbot.process_cmd for my thoughts.


def get_incoming_msg(req: Request) -> Tuple[str, str]:
    """Get an incoming message sent to the bot.

    Arguments:
        req -- Flask Request object

    Returns:
        The first word of and the entirety of the message contents from a POST
            request to the bot as a tuple.
    """
    msg = req.values.get("Body", "/say", str).strip()
    word_1 = msg.split()[0].lower()
    return (word_1, msg)


# TODO: theoretically we could support multiple bots on one server, but
# they'd each need their own routing. Use case for blueprints? Might also
# want to try the routes as keys in a dictionary containing Chatbot objects.
@app.route("/bot", methods=["POST"])
def bot() -> str:
    """Bot's response to a request.

    Returns:
        The bot's response.
    """
    (cmd, msg) = get_incoming_msg(request)
    # TODO: could return Chatbot.process_cmd(cmd, msg)

    # Test: texting me and my mom a message :) it works!
    # mr_botty.push("This is a push message from Halle. Hi!", [
    #               "+15106485015", "+15104104268"])
    return mr_botty.reply('You said: "' + msg + '"')
