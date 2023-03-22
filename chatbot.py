# mypy: disable-error-code=import

"""Basic functionality for a WhatsApp chatbot.

This module contains the class definition to create Chatbot objects, each of
which can support one group of subscribers on WhatsApp. It also contains an
instance of such a chatbot for import by the Flask app.
"""

import json
import os
from types import SimpleNamespace
from typing import Dict, TypedDict

from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from language_data import LangData, translate_to

consts = SimpleNamespace()
# Constant strings for bot commands
consts.TEST = "/test"  # test translate
consts.ADD = "/add"  # add user
consts.REMOVE = "/remove"  # remove user
consts.ADMIN = "/admin"  # toggle admin vs. user role for user
consts.LIST = "/list"  # list all users
consts.LANG = "/lang"  # set language for user
# Roles for users in JSON file
consts.USER = "user"  # can only execute test translation command
consts.ADMIN = "admin"  # can execute all slash commands but cannot remove super
consts.SUPER = "super"  # can execute all slash commands, no limits


class SubscribersInfo(TypedDict):
    """A TypedDict to describe a subscriber.

    For use as the values in a subscribers member of a Chatbot instance, the
    keys to which are to be strings of WhatsApp contact information of the form
    "whatsapp:<phone number with country code>".
    """
    name: str  # username registered with WhatsApp
    lang: str  # user's preferred language code
    role: str  # user's privilege level, "user", "admin", or "super"


class Chatbot:
    """The chatbot logic.

    Class variables:
        commands -- List of slash commands for the bot
        languages -- Data shared by all chatbots on the server about the
            languages supported by LibreTranslate

    Instance variables:
        client -- Client with which to access the Twilio API
        number -- Phone number the bot texts from
        json_file -- Path to a JSON file containing subscriber data
        subscribers -- Dictionary containing the data loaded from the file

    Methods:
        process_cmd -- Process a slash command and send a reply from the bot
    """
    commands = [
        consts.TEST,
        consts.ADD,
        consts.REMOVE,
        consts.ADMIN,
        consts.LIST,
        consts.LANG]
    """All slash commands for the bot."""

    languages: LangData | None = None
    """Data for all languages supported by LibreTranslate."""

    def __init__(
            self,
            account_sid: str,
            auth_token: str,
            number: str,
            json_file: str = "bot_subscribers/template.json"):
        """Create the ChatBot object and populate class members as needed.

        Arguments:
            account_sid -- Account SID
            auth_token -- Account auth token
            number -- Phone number the bot texts from, including country
                extension
            json_file -- Path to a JSON file containing subscriber data
        """
        if Chatbot.languages is None:
            Chatbot.languages = LangData()
        self.client = Client(account_sid, auth_token)
        self.number = number
        self.json_file = json_file
        with open(json_file, encoding="utf-8") as file:
            self.subscribers: Dict[str, SubscribersInfo] = json.load(file)

    def _reply(self, msg_body: str) -> str:
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

    def _push(self, text: str, sender: str):
        """Push a translated message to one or more recipients.

        Arguments:
            text -- Contents of the message
            sender -- Sender's WhatsApp contact info
        """
        translations: Dict[str, str] = {}  # cache previously translated values
        for s in self.subscribers.keys():
            if s != sender:
                if self.subscribers[s]["lang"] in translations:
                    translated = translations[self.subscribers[s]["lang"]]
                else:
                    translated = translate_to(
                        text, self.subscribers[s]["lang"])
                    translations[self.subscribers[s]["lang"]] = translated
                msg = self.client.messages.create(
                    from_=f"whatsapp:{self.number}",
                    to=s,
                    body=translated)
                print(msg.sid)

    def _test_translate(self, msg: str, sender: str) -> str:
        """Translate a string to a language, then to a user's native language.

        Arguments:
            msg -- message to translate
            sender -- number of the user requesting the translation

        Returns:
            The translated message.
        """
        sender_lang = self.subscribers[sender]["lang"]
        try:
            l = msg.split()[1].lower()
            # TODO: replace with dictionary solution for task 235
            if l not in Chatbot.languages.codes:  # type: ignore [union-attr]
                return Chatbot.languages.get_test_err(  # type: ignore [union-attr]
                    sender_lang)
        except IndexError:
            return Chatbot.languages.get_test_err(  # type: ignore [union-attr]
                sender_lang)
        # Translate to requested language then back to native language
        translated = translate_to("".join(msg.split()[2:]), l)
        return translate_to(translated, sender_lang)

    def process_msg(
            self,
            msg: str,
            sender_contact: str,
            sender_name: str) -> str:
        """Process a bot command.

        Arguments:
            msg -- the message sent to the bot
            sender_contact -- the WhatsApp contact info of the sender
            sender_name -- the WhatsApp profile name of the sender

        Returns:
            A string suitable for returning from a Flask route endpoint.
        """
        try:
            sender = self.subscribers[sender_contact]
            role = sender["role"]
        except KeyError:
            return ""  # ignore; they aren't subscribed

        word_1 = msg.split()[0].lower()
        if role == consts.USER:
            if word_1 == consts.TEST:  # test translate
                return self._reply(self._test_translate(msg, sender_contact))
            else:  # just send a message
                text = sender_name + " says:\n" + msg
                self._push(text, sender_contact)
        else:
            match word_1:
                case consts.TEST:  # test translate
                    return self._reply(
                        self._test_translate(
                            msg, sender_contact))
                case consts.ADD:  # add user to subscribers
                    # TODO:
                    pass
                case consts.REMOVE:  # remove user from subscribers
                    # TODO:
                    pass
                case consts.ADMIN:  # toggle user -> admin or admin -> user
                    # TODO:
                    pass
                case consts.LIST:  # list all subscribers with their data
                    subscribers = json.dumps(self.subscribers, indent=2)
                    return self._reply(f"List of subscribers:\n{subscribers}")
                case consts.LANG:  # change preferred language of user
                    # TODO:
                    pass
                case _:  # just send a message
                    text = sender_name + " says:\n" + msg
                    self._push(text, sender_contact)
        return ""


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
