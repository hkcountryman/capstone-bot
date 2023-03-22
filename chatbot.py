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


def _get_timeout() -> int:
    """Populate the timeout constant from the environment.

    Returns:
        The integer value of the environment variable TRANSLATION_TIMEOUT, or 5
            if the variable is nonnumeric or nonexistent.
    """
    try:
        return int(os.getenv("TRANSLATION_TIMEOUT"))  # type: ignore [arg-type]
    except (ValueError, TypeError):
        return 5


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
# Translation API
consts.MIRRORS = [url + "translate" for url in os.getenv(  # list of mirrors
    "LIBRETRANSLATE").split()]  # type: ignore [union-attr]
consts.TIMEOUT = _get_timeout()  # seconds before requests time out


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
        languages -- List of language names, codes, and translation targets
            supported by LibreTranslate
        valid_codes -- List of all languages codes supported by LibreTranslate
        valid_langs -- List of all human-readable languages supported by
            LibreTranslate

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
        consts.TEST,
        consts.ADD,
        consts.REMOVE,
        consts.ADMIN,
        consts.LIST,
        consts.LANG]
    """All slash commands for the bot."""

    languages: List[LanguageInfo] = []
    """All language names, codes, and translation targets of LibreTranslate."""

    valid_codes: List[str] = []
    """List of language codes."""

    valid_langs: List[str] = []
    """List of human-readable language names and their codes."""

    lang_err = ""
    """The portion of an error message containing a list of valid languages."""

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
        if len(Chatbot.languages) == 0:
            # Attempt to populate an up-to-date language models list:
            idx = 0  # index in URLs
            res = None
            while res is None and idx < len(consts.MIRRORS):
                try:
                    res = requests.get(
                        f"{os.getenv('LIBRETRANSLATE')}languages",
                        timeout=consts.TIMEOUT)
                except TimeoutError:
                    idx = idx + 1
            if res is not None and res.status_code == 200:
                Chatbot.languages = res.json()
            else:
                # If that failed, we can load the data from languages.json
                with open("languages.json", encoding="utf-8") as file:
                    Chatbot.languages = json.load(file)
            Chatbot.valid_codes = [x["code"] for x in Chatbot.languages]
            Chatbot.valid_langs = [x["name"] for x in Chatbot.languages]
            Chatbot.lang_err = "".join(["Languages:"] + list(
                map(lambda l: ("\n" + l), Chatbot.valid_langs)))
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
        """Push a message to one or more recipients given their numbers.

        Arguments:
            text -- Contents of the message
            sender -- Sender's WhatsApp contact info
        """
        for s in self.subscribers.keys():
            if s != sender:
                translated = _translate_to(
                    text, self.subscribers[s]["lang"])
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
        error = _translate_to(
            "Choose a valid language. Example:",
            sender_lang) + "\n/test es How are you today?\n\n" + _translate_to(
            Chatbot.lang_err,
            sender_lang)
        try:
            lang = msg.split()[1].lower()
            # TODO: replace with dictionary solution for task 235
            if lang not in Chatbot.languages:
                return error
        except IndexError:
            return error
        # Translate to requested language then back to native language
        translated = _translate_to("".join(msg.split()[2:]), lang)
        return _translate_to(translated, self.subscribers[sender]["lang"])

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
                # TODO:
                pass
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


def _translate_to(text: str, target_lang: str) -> str:
    """Translate text to the target language using the LibreTranslate API.

    Arguments:
        text -- The text to be translated
        target_lang -- The target language code ("en", "es", "fr", etc.)

    Returns:
        Translated text
    """
    payload = {"q": text, "source": "auto", "target": target_lang}
    idx = 0  # index in URLs
    res = None
    while res is None and idx < len(consts.MIRRORS):
        try:
            res = requests.post(
                consts.MIRRORS[idx],
                data=payload,
                timeout=consts.TIMEOUT)
        except TimeoutError:
            idx = idx + 1
    if res is None:  # ran out of mirrors to try
        return "Translation timed out"
    elif res.status_code == 200:
        return res.json()["translatedText"]
    else:
        return f"Translation failed: HTTP {res.status_code} {res.reason}"


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
