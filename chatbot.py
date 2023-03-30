# mypy: disable-error-code=import

"""Basic functionality for a WhatsApp chatbot.

This module contains the class definition to create Chatbot objects, each of
which can support one group of subscribers on WhatsApp. It also contains an
instance of such a chatbot for import by the Flask app.
"""

import json
import os
from types import SimpleNamespace
from typing import Dict, List, TypedDict

import requests
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
consts.VALID_ROLES = [consts.USER, consts.ADMIN, consts.SUPER]


class SubscribersInfo(TypedDict):
    """A TypedDict to describe a subscriber.

    For use as the values in a subscribers member of a Chatbot instance, the
    keys to which are to be strings of WhatsApp contact information of the form
    "whatsapp:<phone number with country code>".
    """
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
            json_file: str = "bot_subscribers/team56test.json"):
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
        self.twilio_account_sid = account_sid
        self.twilio_auth_token = auth_token
        self.twilio_number = number
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

    def _push(
            self,
            text: str,
            sender: str,
            media_urls: List[str] = "") -> str:
        """Push a translated message and media to one or more recipients.

        Arguments:
            text -- Contents of the message
            sender -- Sender's WhatsApp contact info
            media_urls -- a list of media URLs to send, if any

        Returns:
            An empty string to the sender, or else an error message if the
                request to the LibreTranslate API times out or has some other
                error.
        """
        if media_urls is None:
            media_urls = []

        translations: Dict[str, str] = {}  # cache previously translated values
        for s in self.subscribers.keys():
            if s != sender:
                if self.subscribers[s]["lang"] in translations:
                    translated = translations[self.subscribers[s]["lang"]]
                else:
                    try:
                        translated = translate_to(
                            text, self.subscribers[s]["lang"])
                    except (TimeoutError, requests.HTTPError) as e:
                        return str(e)
                    translations[self.subscribers[s]["lang"]] = translated
                msg = self.client.messages.create(
                    from_=f"whatsapp:{self.number}",
                    to=s,
                    body=translated,
                    media_url=media_urls)  # Include media_urls in the message
                print(msg.sid)
        return ""

    def _test_translate(self, msg: str, sender: str) -> str:
        """Translate a string to a language, then to a user's native language.

        Arguments:
            msg -- message to translate
            sender -- number of the user requesting the translation

        Returns:
            The translated message, or else an error message if the request to
                the LibreTranslate API times out or has some other error.
        """
        sender_lang = self.subscribers[sender]["lang"]
        try:
            l = msg.split()[1].lower()
            if l not in Chatbot.languages.codes:  # type: ignore [union-attr]
                return Chatbot.languages.get_test_example(  # type: ignore [union-attr]
                    sender_lang)
        except IndexError:
            return Chatbot.languages.get_test_example(  # type: ignore [union-attr]
                sender_lang)
        # Translate to requested language then back to native language
        text = " ".join(msg.split()[2:])
        if text != "":
            try:
                translated = translate_to(text, l)
                return translate_to(translated, sender_lang)
            except (TimeoutError, requests.HTTPError) as e:
                return str(e)
        return Chatbot.languages.get_test_example(  # type: ignore [union-attr]
            sender_lang)

    def send_media_message(
            self,
            recipient_number: str,
            media_url: str,
            text: str = ""):
        client = Client(self.twilio_account_sid, self.twilio_auth_token)
        message_data = {
            "from": f"whatsapp:{self.twilio_number}",
            "to": f"whatsapp:{recipient_number}",
            "media_url": media_url,
        }
        if text:
            message_data["body"] = text
        client.messages.create(**message_data)

    def add_subscriber(self, msg: str, sender_contact: str) -> str:
        """Add a new subscriber to the dictionary and save it to the JSON file.

        Arguments:
            msg -- the message sent to the bot
            sender_contact -- WhatsApp contact info of the sender

        Returns:
            A string suitable for returning from a Flask route endpoint.
        """
        sender_lang = self.subscribers[sender_contact]["lang"]

        # Split the message into parts
        parts = msg.split()

        # Check if there are enough arguments
        if len(parts) == 4:
            new_contact, new_lang, new_role = parts[1], parts[2], parts[3]

            # Check if the role is valid
            if new_role not in consts.VALID_ROLES:
                return Chatbot.languages.get_add_rol_err(  # type: ignore [union-attr]
                    sender_lang)

            # Check if the language code is valid
            if new_lang not in\
                    Chatbot.languages.codes:  # type: ignore [union-attr]
                return Chatbot.languages.get_add_lng_err(  # type: ignore [union-attr]
                    sender_lang)

            new_contact_key = f"whatsapp:{new_contact}"
            # Check if the user already exists
            if new_contact_key in self.subscribers:
                return Chatbot.languages.get_exists_err(  # type: ignore [union-attr]
                    sender_lang)

            self.subscribers[new_contact_key] = {
                "lang": new_lang,
                "role": new_role
            }

            # Save the updated subscribers to team56test.json
            with open(self.json_file, "w", encoding="utf-8") as f:  # TODO: locking mechanism
                json.dump(self.subscribers, f, indent=4)

            return Chatbot.languages.get_add_success(  # type: ignore [union-attr]
                sender_lang)
        else:
            return Chatbot.languages.get_add_err(  # type: ignore [union-attr]
                sender_lang)

    def remove_subscriber(self, msg: str, sender_contact: str) -> str:
        """
        Remove a subscriber from the dictionary and save the updated dictionary.

        to the JSON file.

        Arguments:
            msg -- the message sent to the bot
            sender_contact -- WhatsApp contact info of the sender

        Returns:
            A string suitable for returning from a Flask route endpoint,
                indicating the result of the removal attempt.
        """
        sender_lang = self.subscribers[sender_contact]["lang"]
        sender_role = self.subscribers[sender_contact]["role"]

        # Split the message into parts
        parts = msg.split()

        # Check if there are enough arguments
        if len(parts) == 2:
            user_contact = parts[1]
            user_contact_key = f"whatsapp:{user_contact}"

            # Prevent sender from removing themselves
            # sender_contact = 2345678900 and user_contact = +12345678900
            # TODO: Need a way to fix this.
            if sender_contact == user_contact:
                return Chatbot.languages.get_remove_self_err(  # type: ignore [union-attr]
                    sender_lang)

            # Check if the user exists
            if user_contact_key not in self.subscribers:
                return Chatbot.languages.get_unfound_err(  # type: ignore [union-attr]
                    sender_lang)

            # Check if the sender has the necessary privileges
            if sender_role == consts.ADMIN and self.subscribers[
                    user_contact_key]["role"] == consts.SUPER:
                return Chatbot.languages.get_remove_super_err(  # type: ignore [union-attr]
                    sender_lang)
            else:
                del self.subscribers[user_contact_key]

                # Save the updated subscribers to team56test.json
                with open(self.json_file, 'w', encoding="utf-8") as f:  # TODO: locking mechanism
                    json.dump(self.subscribers, f, indent=4)

                return Chatbot.languages.get_remove_success(  # type: ignore [union-attr]
                    sender_lang)
        else:
            return Chatbot.languages.get_remove_err(  # type: ignore [union-attr]
                sender_lang)

    def process_msg(
            self,
            msg: str,
            sender_contact: str,
            sender_name: str,
            media_urls: List[str]) -> str:
        """Process a bot command.

        Arguments:
            msg -- the message sent to the bot
            sender_contact -- the WhatsApp contact info of the sender
            sender_name -- the WhatsApp profile name of the sender
            media_urls -- a list of media URLs sent with the message, if any

        Returns:
            A string suitable for returning from a Flask route endpoint.
        """
        try:
            sender = self.subscribers[sender_contact]
            role = sender["role"]
        except KeyError:
            return ""  # ignore; they aren't subscribed

        if not msg and not media_urls:
            return "Please send a text or media message."

        if msg:
            word_1 = msg.split()[0].lower()
        else:
            word_1 = ""

        if role == consts.USER:
            if word_1 == consts.TEST:  # test translate
                return self._reply(self._test_translate(msg, sender_contact))
            elif word_1[0:1] == "/" and len(word_1) > 1:
                return ""  # ignore invalid/unauthorized command
            else:  # just send a message
                text = sender_name + " says:\n" + msg
                self._push(text, sender_contact)
                return ""  # say nothing to sender
        else:
            match word_1:
                case consts.TEST:  # test translate
                    return self._reply(
                        self._test_translate(
                            msg, sender_contact))
                case consts.ADD:  # add user to subscribers
                    # Call the add_subscriber method and return its response
                    return self._reply(
                        self.add_subscriber(
                            msg, sender_contact))
                case consts.REMOVE:  # remove user from subscribers
                    return self._reply(
                        self.remove_subscriber(
                            msg, sender_contact))
                case consts.LIST:  # list all subscribers with their data
                    subscribers = json.dumps(self.subscribers, indent=2)
                    return self._reply(f"List of subscribers:\n{subscribers}")
                case _:  # just send a message
                    if word_1[0:1] == "/" and len(word_1) > 1:
                        return ""  # ignore invalid/unauthorized command
                    text = sender_name + " says:\n" + msg
                    return self._push(text, sender_contact, media_urls)
        # Send media messages, if any
        for media_url in media_urls:
            self.send_media_message(sender_contact, media_url)
        return ""  # return an empty string when the message is processed


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
