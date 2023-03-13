"""A simple WhatsApp bot."""

from flask import Flask, Response, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)


@app.route("/bot", methods=["POST"])
def bot() -> Response:
    """Bot's response to a request.

    In this function, you can refer to the identifier `request` to access the
    object of type flask.Request:
    https://flask.palletsprojects.com/en/2.2.x/reqcontext/
    https://flask.palletsprojects.com/en/2.2.x/api/#flask.Request

    Returns:
        the bot's response.
    """
    # Defaults to "", type str:
    incoming_msg = request.values.get("Body", "", str)

    resp = MessagingResponse()
    msg = resp.message()
    msg.body('You said: "' + incoming_msg + '"')
    msg.media("/static/imgs/cat.png")

    return str(resp)
