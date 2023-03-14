"""Basic functionality for a WhatsApp chatbot.

This module contains the class definition to create Chatbot objects, each of
which can support one group of subscribers on WhatsApp. It also contains an
instance of such a chatbot for import by the Flask app.
"""

from os import getenv
from typing import List

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse


class Chatbot:
    """The chatbot logic.

    Class variables:
        commands -- List of slash commands for the bot

    Instance variables:
        client -- Client with which to access the Twilio API
        number -- Phone number the bot texts from

    Methods:
        reply -- Reply to a message to the bot
        push -- Push a message to one or more recipients given their numbers
        process_cmd -- Process a slash command and send a reply from the bot
    """

    commands = [
        "/say",
        "/y",
        "/n",
        "/czech",
        "/english",
        "/spanish",
        "/ukranian"]

    def __init__(
            self,
            account_sid: str,
            auth_token: str,
            number: str,
            subscribers: str = "bot_subscribers/template.json"):
        """Create the ChatBot object.

        Arguments:
            account_sid -- Account SID
            auth_token -- Account auth token
            number -- Phone number the bot texts from
            subscribers -- Path to a JSON file containing subscriber data
        """
        self.client = Client(account_sid, auth_token)
        self.number = number
        self.subscribers = subscribers

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
            recipients -- List of phone numbers with country extension codes
        """
        for r in recipients:
            msg = self.client.messages.create(
                from_=f"whatsapp:{self.number}",
                to=f"whatsapp:{r}",
                body=msg_body)
            print(msg.sid)

    # TODO: Idea: slash commands with an optional /say command, like how you
    # can preface a message in an IRC client with "/say" in order to send a
    # message that may even start with a slash command. If the message starts
    # with "/say" or no slash command, it can be assumed to be a message to
    # the group.
    @staticmethod
    def process_cmd(cmd: str, msg: str = None) -> str:
        """Process a bot command.

        Arguments:
            cmd -- the command to process

        Keyword Arguments:
            msg -- the message to translate and relay, if applicable
                (default: {None})

        Returns:
            A string suitable for returning from a Flask route endpoint.
        """
        # Ensure command is valid; otherwise assume it was just the first word
        # in a message:
        c = "/say" if cmd not in Chatbot.commands else cmd
        # If message exists and starts with "/say", trim that:
        m = msg[4:].strip() if msg is not None and cmd == "/say" else msg
        match c:
            case "/say":  # say a message to the group
                # TODO: update json file to contain message, do not send but
                # prompt user to confirm and send or enter further commands
                pass
            case "/y":  # proceed to send message
                # TODO: if json file has a message for this user, translate and
                # send, then clear it from json file
                pass
            case "/n":  # cancel sending message
                # TODO: if json file has a message for this user, clear it
                pass
            case language:  # other commands must be language names
                lang = c[1:]  # remove leading slash
                # TODO: if json file has a message for this user, translate to
                # lang and show them the result; do not clear it
                # TODO: if json file does not have a message for this user, set
                # user's preferred language to lang
                pass
        return ""  # TODO: whatever is returned is sent to user who sent command


mr_botty = Chatbot(
    getenv("TWILIO_ACCOUNT_SID"),
    getenv("TWILIO_AUTH_TOKEN"),
    getenv("TWILIO_NUMBER"))  # TODO: add subscriber JSON file
"""Global Chatbot object, of which there could theoretically be many."""
