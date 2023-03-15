"""Basic functionality for a WhatsApp chatbot.

This module contains the class definition to create Chatbot objects, each of
which can support one group of subscribers on WhatsApp. It also contains an
instance of such a chatbot for import by the Flask app.
"""

import json
import os
from types import SimpleNamespace
from typing import List

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

# Constant strings for bot commands
consts = SimpleNamespace()
consts.DRAFT_MSG = "/say"
consts.SEND_MSG = "/y"
consts.CANCEL_MSG = "/n"
consts.UNSUBSCRIBE = "/unsubscribe"
consts.CZECH = "/czech"
consts.ENGLISH = "/english"
consts.SPANISH = "/spanish"
consts.UKRANIAN = "/ukranian"


class Chatbot:
    """The chatbot logic.

    Class variables:
        commands -- List of slash commands for the bot

    Instance variables:
        client -- Client with which to access the Twilio API
        number -- Phone number the bot texts from
        json_file -- Path to a JSON file containing subscriber data
        subscribers -- Dictionary containing the data loaded from the file

    Methods:
        reply -- Reply to a message to the bot
        push -- Push a message to one or more recipients given their numbers
        process_cmd -- Process a slash command and send a reply from the bot
    """

    commands = [
        consts.DRAFT_MSG,
        consts.SEND_MSG,
        consts.CANCEL_MSG,
        consts.UNSUBSCRIBE,
        consts.CZECH,
        consts.ENGLISH,
        consts.SPANISH,
        consts.UKRANIAN]

    def __init__(
            self,
            account_sid: str,
            auth_token: str,
            number: str,
            json_file: str = "bot_subscribers/template.json"):
        """Create the ChatBot object.

        Arguments:
            account_sid -- Account SID
            auth_token -- Account auth token
            number -- Phone number the bot texts from, including country
                extension
            json_file -- Path to a JSON file containing subscriber data
        """
        self.client = Client(account_sid, auth_token)
        self.number = number
        self.json_file = json_file
        with open(json_file, encoding="utf-8") as file:
            self.subscribers = json.load(file)

    def reply(self, msg_body: str) -> str:
        """Reply to a message to the bot.

        Arguments:
            msg_body -- Contents to reply with

        Returns:
            A string suitable for returning from a route function.
        """
        resp = MessagingResponse()
        msg = resp.message()
        msg.body(msg_body)
        return str(resp)

    def push(self, msg_body: str, recipients: List[str]):
        """Push a message to one or more recipients given their numbers.

        Arguments:
            msg_body -- Contents of the message
            recipients -- List of recipients' WhatsApp contact info (see key in
                bot_subscribers/template.json for an example of how these are
                formatted)
        """
        for r in recipients:
            msg = self.client.messages.create(
                from_=f"whatsapp:{self.number}",
                to=r,
                body=msg_body)
            print(msg.sid)

    # TODO: Idea: slash commands with an optional /say command, like how you
    # can preface a message in an IRC client with "/say" in order to send a
    # message that may even start with a slash command. If the message starts
    # with "/say" or no slash command, it can be assumed to be a message to
    # the group.
    @staticmethod
    def process_cmd(
            cmd: str,
            msg: str,
            sender_contact: str,
            sender_name: str) -> str:
        """Process a bot command.

        Arguments:
            cmd -- the command to process
            msg -- the entire message sent to the bot
            sender_contact -- the WhatsApp contact info of the sender
            sender_name -- the WhatsApp profile name of the sender

        Returns:
            A string suitable for returning from a Flask route endpoint.
        """
        # Ensure command is valid; if not, assume it was just the first word in
        # a message:
        c = consts.DRAFT_MSG if cmd not in Chatbot.commands else cmd
        # If message exists and starts with "/say", trim that:
        m = msg[len(consts.DRAFT_MSG):].strip(
        ) if cmd == consts.DRAFT_MSG else msg
        # TODO: confirm sender is among self.subscribers keys and add them if
        # not
        match c:
            case consts.DRAFT_MSG:  # say a message to the group
                # TODO: update json file to contain message, do not send but
                # prompt user to confirm and send or enter further commands
                pass
            case consts.SEND_MSG:  # proceed to send message
                # TODO: if self.subscribers has a message for this user,
                # translate and send to all keys of self.subscribers except
                # that matching sender, then set self.subscribers[sender][msg]
                # to None
                pass
            case consts.CANCEL_MSG:  # cancel sending message
                # TODO: if self.subscribers has a message for this user, then
                # set self.subscribers[sender][msg] to None
                pass
            case consts.UNSUBSCRIBE:  # unsubscribe from bot
                # TODO: remove this user from self.subscribers and inform them
                # they can text the bot again to re-subscribe
                pass
            case language:  # other commands must be language names
                lang = c[1:]  # remove leading slash
                # TODO: if self.subscribers has a message for this user,
                # translate to lang and show them the result; do not alter
                # self.subscribers[sender][msg]
                # TODO: if self.subscribers does not have a message for this
                # user, set self.subscribers[sender][lang] to lang
                pass
        return ""  # TODO: whatever is returned is sent to user who sent command


mr_botty = Chatbot(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN"),
    os.getenv("TWILIO_NUMBER"))  # TODO: add subscriber JSON file
"""Global Chatbot object, of which there could theoretically be many."""
