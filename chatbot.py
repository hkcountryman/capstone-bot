# mypy: disable-error-code=import

"""Basic functionality for a WhatsApp chatbot.

This module contains the class definition to create Chatbot objects, each of
which can support one group of subscribers on WhatsApp. It also contains an
instance of such a chatbot for import by the Flask app.
"""
import json
import os
from types import SimpleNamespace
from typing import Dict, List

import requests
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

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
# Languages
consts.CZECH = "czech"
consts.ENGLISH = "english"
consts.SPANISH = "spanish"
consts.UKRANIAN = "ukranian"
# Translate API
if os.getenv("LIBRETRANSLATE") is not None:
    consts.MIRRORS = [
        url + "translate" for url in
        os.getenv("LIBRETRANSLATE").split()]  # type: ignore [union-attr]
else:
    consts.MIRRORS = []


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
        consts.TEST,
        consts.ADD,
        consts.REMOVE,
        consts.ADMIN,
        consts.LIST,
        consts.LANG]

    languages = [consts.CZECH, consts.ENGLISH, consts.SPANISH, consts.UKRANIAN]

    test_err = "".join([
        "Please provide a valid language to test with. Example:\n" +
        "\t/test spanish Hello everybody!\nValid languages:"
    ] + list(map(lambda l: ("\n" + l.capitalize()), languages)))

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
            self.subscribers: Dict[str, Dict[str, str]] = json.load(file)

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

    @staticmethod
    def translate_to(text: str, target_lang: str) -> str:
        """Translate text to the target language using the LibreTranslate API.

        Arguments:
            text -- The text to be translated
            target_lang -- The target language code ('en', 'es', 'fr', etc.)

        Returns:
            Translated text
        """
        payload = {"q": text, "source": "auto", "target": target_lang}
        to = os.getenv("TRANSLATION_TIMEOUT")
        timeout = int(to) if to is not None else 5
        idx = 0  # index in urls
        res = None
        while res is None and idx < len(consts.MIRRORS):
            try:
                res = requests.post(
                    consts.MIRRORS[idx],
                    data=payload,
                    timeout=timeout)
            except TimeoutError:
                idx = idx + 1
        if res is None:  # ran out of mirrors to try
            return "Translation timed out"
        elif res.status_code == 200:
            return res.json()["translatedText"]
        else:
            return f"Translation failed: HTTP {res.status_code} {res.reason}"

    @staticmethod
    def test_translate(msg: str, sender: str):
        """Translate a string to a language, then to a user's native language.

        Arguments:
            msg -- message to translate
            sender -- number of the user requesting the translation

        Returns:
            The translated message.
        """
        try:
            lang = msg.split()[1].lower()
            # TODO: replace with dictionary solution for task 235
            # if lang not in Chatbot.languages:
            #     return Chatbot.test_err
        except IndexError:
            return Chatbot.test_err
        # Translate to requested language then back to native language
        translated = Chatbot.translate_to(
            "".join(msg.split()[2:]), lang)
        # TODO: replace with dictionary solution for task 235
        return Chatbot.translate_to(translated, "en")  # sender["lang"])

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
                return self.reply(Chatbot.test_translate(msg, sender_contact))
            else:  # just send a message
                # TODO:
                pass
        else:
            match word_1:
                case consts.TEST:  # test translate
                    return self.reply(
                        Chatbot.test_translate(
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
                    return self.reply(f"List of subscribers:\n{subscribers}")
                case consts.LANG:  # change preferred language of user
                    # TODO:
                    pass
                case _:  # just send a message
                    # TODO: actually send, put the translate logic in send
                    translated_msg = self.translate_to(msg, "es")
                    return self.reply(f"Translated message: {translated_msg}")
        return ""  # TODO: whatever is returned is sent to user who sent command


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
