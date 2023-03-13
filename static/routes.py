"""Serve static content at /static/imgs/[image name]."""

from flask import Blueprint

# https://flask.palletsprojects.com/en/2.2.x/blueprints/#static-files
static_bp: Blueprint = Blueprint(
    "static",
    __name__,
    static_folder="imgs",
    url_prefix="/static")
