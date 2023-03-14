"""Serve static content at /static/imgs/[image name].

A twillio.twiml.messaging_response.MessagingResponse object `msg` may include an
image by setting, for example, `msg.media("/static/imgs/cat.png")`.
"""

from flask import Blueprint

# https://flask.palletsprojects.com/en/2.2.x/blueprints/#static-files
static_bp: Blueprint = Blueprint(
    "static",
    __name__,
    static_folder="imgs",
    url_prefix="/static")
