"""A Flask server for the WhatsApp chatbot.

This module handles the route to make requests to the bot.
"""

from typing import Tuple

from flask import Flask, Request, request

from chatbot import Chatbot, consts, mr_botty

app = Flask(__name__)
"""The server running the chatbot."""


# TODO: functions to determine whether message is message to the group or a
# bot command. May use switch case to parse first word of message once
# trimmed of leading whitespace. I'm thinking
#
# See match case in Chatbot.process_cmd for my thoughts.


def get_incoming_msg(req: Request) -> Tuple[str, str, str, str]:
    """Get an incoming message sent to the bot and its sender.

    Arguments:
        req -- Flask Request object

    Returns:
        The first word of and the entirety of the message contents from a POST
            request to the bot as well as the sender contact info and name.
    """
    msg = req.values.get("Body", default=consts.DRAFT_MSG, type=str).strip()
    word_1 = msg.split()[0].lower()
    sender_contact = request.values.get("From", type=str)
    sender_name = request.values.get("ProfileName", type=str)
    return (word_1, msg, sender_contact, sender_name)


# TODO: theoretically we could support multiple bots on one server, but
# they'd each need their own routing. Use case for blueprints? Might also
# want to try the routes as keys in a dictionary containing Chatbot objects.
@app.route("/bot", methods=["POST"])
def bot() -> str:
    """Bot's response to a request.

    Returns:
        The bot's response.
    """
    # request.values:
    # 'SmsMessageSid', 'SM365da26a1c92746da810854c457380ff'
    # 'NumMedia', '0'
    # 'ProfileName', 'Halle Countryman'
    # 'SmsSid', 'SM365da26a1c92746da810854c457380ff'
    # 'WaId', '15104104268'
    # 'SmsStatus', 'received'
    # 'Body', 'Request'
    # 'To', 'whatsapp:+14155238886'
    # 'NumSegments', '1'
    # 'ReferralNumMedia', '0'
    # 'MessageSid', 'SM365da26a1c92746da810854c457380ff'
    # 'AccountSid', 'ACef099c27b98ddc3a910d6564f6e53a8d'
    # 'From', 'whatsapp:+15104104268'
    # 'ApiVersion', '2010-04-01'
    (cmd, msg, sender_contact, sender_name) = get_incoming_msg(request)
    # TODO: return Chatbot.process_cmd(cmd, msg, sender_contact, sender_name)
    return mr_botty.reply('You said: "' + msg + '"')
