# mypy: disable-error-code=import

"""Basic functionality for a WhatsApp chatbot.

This module contains the class definition to create Chatbot objects, each of
which can support one group of subscribers on WhatsApp. It also contains an
instance of such a chatbot for import by the Flask app.

Classes:
    SubscribersInfo -- A TypedDict to describe a subscriber to the group chat
    Chatbot -- A class to keep track of data about a group chat and its
        associated WhatsApp bot
"""

import json
import os
import re
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Dict, List, TypedDict

import requests
from cryptography.fernet import Fernet
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
consts.STATS = "/stats"  # get stats for user
consts.LASTPOST = "/lastpost"  # get last post for user
consts.TOTALSTATS = "/totalstats"  # get total stats for all users

# Roles for users in JSON file
consts.USER = "user"  # can only execute test translation command
consts.ADMIN = "admin"  # can execute all slash commands but cannot remove super
consts.SUPER = "super"  # can execute all slash commands, no limits
consts.VALID_ROLES = [consts.USER, consts.ADMIN, consts.SUPER]

pm_char = "#"  # Example: #xX_bob_Xx Hey bob, this is a private message!


class SubscribersInfo(TypedDict):
    """A TypedDict to describe a subscriber.

    For use as the values in a subscribers member of a Chatbot instance, the
    keys to which are to be strings of WhatsApp contact information of the form
    "whatsapp:<phone number with country code>".
    """
    name: str  # user's display name
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
        display_names -- Dictionary mapping display names to WhatsApp numbers
            for subscribers
        twilio_account_sid -- Account SID for the Twilio account
        twilio_auth_token -- Twilio authorization token
        twilio_number -- Bot's registered Twilio number

    Methods:
        process_msg -- Process a message to the bot
    """
    commands = [
        consts.TEST,
        consts.ADD,
        consts.REMOVE,
        consts.ADMIN,
        consts.LIST,
        consts.LANG,
        consts.STATS,
        consts.LASTPOST,
        consts.TOTALSTATS]
    """All slash commands for the bot."""

    languages: LangData | None = None
    """Data for all languages supported by LibreTranslate."""

    def __init__(
            self,
            account_sid: str,
            auth_token: str,
            number: str,
            json_file: str = "json/team56test.json",
            backup_file: str = "json/backup.json",
            key_file: str = "json/key.key",
            logs_file: str = "logs.json"):
        """Create the ChatBot object and populate class members as needed.

        Arguments:
            account_sid -- Account SID
            auth_token -- Account auth token
            number -- Phone number the bot texts from, including country
                extension

        Keyword Arguments:
            json_file -- Path to a JSON file containing subscriber data
                (default: {"json/team56test.json"})
            backup_file -- Path to a JSON file containing backup data for the
                above JSON file (default: {"json/backup.json"})
            key_file -- Path to a file containing the encryption key (default:
                {"json/key.key"})
            logs_file -- Path to a JSON file where chat timestamps are stored
                (default: {"logs.json"})
        """
        if Chatbot.languages is None:
            Chatbot.languages = LangData()
        self.client = Client(account_sid, auth_token)
        self.number = number
        self.json_file = json_file
        self.backup_file = backup_file
        self.key_file = key_file
        self.logs_file = logs_file
        self.twilio_account_sid = account_sid
        self.twilio_auth_token = auth_token
        self.twilio_number = number
        # TODO: Kevin, does this need to be encrypted and backed up?
        try:
            with open(self.logs_file, "r", encoding="utf-8") as file:
                self.logs = json.load(file)
        except FileNotFoundError:
            self.logs = {}
            with open(self.logs_file, "w", encoding="utf-8") as file:
                json.dump(self.logs, file)
        with open(self.json_file, "rb") as file:
            encrypted_data = file.read()
        with open(self.key_file, "rb") as file:
            self.key = file.read()  # Retrieve encryption key
        f = Fernet(self.key)
        try:
            unencrypted_data = f.decrypt(encrypted_data).decode("utf-8")
            self.subscribers: Dict[str, SubscribersInfo] = json.loads(
                unencrypted_data)
        except BaseException:  # pylint: disable=broad-exception-caught
            # Handle corrupted file
            # TODO: Print message to super administrator that original file is
            # corrupted...recent data may not have been saved.
            with open(self.backup_file, "rb") as file:
                backup_encrypted_data = file.read()
            backup_unencrypted_data = f.decrypt(
                backup_encrypted_data).decode("utf-8")
            self.subscribers = json.loads(backup_unencrypted_data)
        self.display_names: Dict[str, str] = {
            v["name"]: k for k, v in self.subscribers.items()}

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

    def _push(self, text: str, sender: str, media_urls: List[str]) -> str:
        """Push a translated message and media to one or more recipients.

        Arguments:
            text -- Contents of the message
            sender -- Sender"s WhatsApp contact info
            media_urls -- a list of media URLs to send, if any

        Returns:
            An empty string to the sender, or else an error message if the
                request to the LibreTranslate API times out or has some other
                error.
        """
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
                    media_url=media_urls)
                print(msg.sid)
        return ""

    # TODO: recipient should work as both username and phone number
    def _query(
            self,
            msg: str,
            sender: str,
            sender_lang: str,
            recipient: str,
            media_urls: List[str]) -> str:
        """Send a private message to a single recipient.

        Arguments:
            msg -- message contents
            sender -- sender display name
            sender_lang -- sender preferred language code
            recipient -- recipient display name
            media_urls -- any attached media URLs from Twilio's CDN

        Returns:
            An empty string to the sender, or else an error message if the
                request to the LibreTranslate API times out or has some other
                error.
        """
        # Check whether recipient exists
        if recipient not in self.display_names:
            return Chatbot.languages.get_unfound_err(  # type: ignore [union-attr]
                sender_lang)
        if not (msg == "" and len(media_urls) == 0):  # something to send
            recipient_contact = self.display_names[recipient]
            recipient_lang = self.subscribers[recipient_contact]["lang"]
            text = f"Private message from {sender}:\n{msg}"
            try:
                translated = translate_to(text, recipient_lang)
            except (TimeoutError, requests.HTTPError) as e:
                return str(e)
            pm = self.client.messages.create(
                from_=f"whatsapp:{self.number}",
                to=recipient_contact,
                body=translated,
                media_url=media_urls)
            print(pm.sid)
        return ""

    def _test_translate(self, msg: str, sender: str) -> str:
        """Translate a string to a language, then to a user"s native language.

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

    def _add_subscriber(self, msg: str, sender_contact: str) -> str:
        """Add a new subscriber to the dictionary and save it to the JSON file.

        Arguments:
            msg -- the message sent to the bot
            sender_contact -- WhatsApp contact info of the sender

        Returns:
            A string suitable for returning from a Flask route endpoint.
        """
        sender_lang = self.subscribers[sender_contact]["lang"]
        sender_role = self.subscribers[sender_contact]["role"]
        parts = msg.split()
        if len(parts) == 5:  # Check if there are enough arguments
            new_contact = parts[1]
            new_name = parts[2]
            new_lang = parts[3]
            new_role = parts[4]
            # Check if the sender has the authority to add the specified role
            if sender_role == consts.ADMIN and new_role == consts.SUPER:
                return ""
            # Check if the phone number is valid
            if (not new_contact.startswith("+")
                ) or (not new_contact[1:].isdigit()):
                return Chatbot.languages.get_add_phone_err(  # type: ignore [union-attr]
                    sender_lang)
            # start attempt to add contact
            new_contact_key = f"whatsapp:{new_contact}"
            # Check if the user already exists
            if new_contact_key in self.subscribers:
                return Chatbot.languages.get_exists_err(  # type: ignore [union-attr]
                    sender_lang)
            # Check if the display name is untaken
            if new_name in self.display_names:
                return Chatbot.languages.get_add_name_err(  # type: ignore [union-attr]
                    sender_lang)
            # Check if the language code is valid
            if new_lang not in\
                    Chatbot.languages.codes:  # type: ignore [union-attr]
                return Chatbot.languages.get_add_lang_err(  # type: ignore [union-attr]
                    sender_lang)
            # Check if the role is valid
            if new_role not in consts.VALID_ROLES:
                return Chatbot.languages.get_add_role_err(  # type: ignore [union-attr]
                    sender_lang)
            self.subscribers[new_contact_key] = {
                "name": new_name,
                "lang": new_lang,
                "role": new_role
            }
            self.display_names[new_name] = new_contact_key
            # Save the updated subscribers to team56test.json
            # Convert the dictionary of subscribers to a formatted JSON string
            subscribers_list = json.dumps(self.subscribers, indent=4)
            # Create byte version of JSON string
            subscribers_list_byte = subscribers_list.encode("utf-8")
            f = Fernet(self.key)
            encrypted_data = f.encrypt(subscribers_list_byte)
            with open(self.json_file, "wb") as file:
                file.write(encrypted_data)
            # Copy data to backup file
            with open(self.json_file, "rb") as fileone, \
                    open(self.backup_file, "wb") as filetwo:
                for line in fileone:
                    filetwo.write(line)
            return Chatbot.languages.get_add_success(  # type: ignore [union-attr]
                sender_lang)
            # TODO: Add new user to the timestamp logs
        else:
            return Chatbot.languages.get_add_err(  # type: ignore [union-attr]
                sender_lang)

    # TODO: user_contact should work as both username and phone number
    def _remove_subscriber(self, msg: str, sender_contact: str) -> str:
        """Remove a subscriber from the dictionary and save the dictionary.

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
        parts = msg.split()
        if len(parts) == 2:  # Check if there are enough arguments
            user_contact = parts[1]
            user_contact_key = f"whatsapp:{user_contact}"
            # Prevent sender from removing themselves
            if user_contact in sender_contact:
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
                name = self.subscribers[user_contact_key]["name"]
                del self.display_names[name]
                del self.subscribers[user_contact_key]
            # Save the updated subscribers to team56test.json
            # Convert the dictionary of subscribers to a formatted JSON string
            subscribers_list = json.dumps(self.subscribers, indent=4)
            # Create byte version of JSON string
            subscribers_list_byte = subscribers_list.encode("utf-8")
            f = Fernet(self.key)
            encrypted_data = f.encrypt(subscribers_list_byte)
            with open(self.json_file, "wb") as file:
                file.write(encrypted_data)
            # Copy data to backup file
            with open(self.json_file, "rb") as fileone, \
                    open(self.backup_file, "wb") as filetwo:
                for line in fileone:
                    filetwo.write(line)
            return Chatbot.languages.get_remove_success(  # type: ignore [union-attr]
                sender_lang)
            # TODO: also remove subscriber's chat logs
        else:
            return Chatbot.languages.get_remove_err(  # type: ignore [union-attr]
                sender_lang)

    def _store_message_timestamp(self, sender_contact: str, msg: str) -> None:
        """Store the timestamp of a message sent by a user.

        Do not count empty PMs or slash commands.

        Arguments:
            sender_contact -- WhatsApp contact info of the sender
            msg -- the message sent to the bot
        """
        # Only proceed if message is not a command and is not an empty PM
        if not msg.startswith("/") and not (msg.startswith(pm_char) and
                                            len(msg.split()) <= 1):
            timestamp = datetime.now().strftime("%Y-%m-%d")
            if sender_contact in self.logs:  # sender is already in log file...
                self.logs[sender_contact]["timestamps"].append(timestamp)
            else:  # otherwise add them to logs before adding timestamp
                self.logs[sender_contact] = {"timestamps": [timestamp]}
            # TODO: Kevin, does this need to be encrypted or anything?
            with open(self.logs_file, "w", encoding="utf-8") as file:
                json.dump(self.logs, file, indent=2)

    def _generate_stats(self, sender_contact: str, msg: str) -> str:
        """Generate message statistics for a specified user and time frame.

        Arguments:
            sender_contact -- WhatsApp contact info of the sender
            msg -- the message sent to the bot, containing the user contact
                and the time frame for statistics

        Returns:
            A string containing the message statistics or an error message
                if the input is incorrect or the user is not found.
        """
        sender_lang = self.subscribers[sender_contact]["lang"]
        split_msg = msg.split()  # Check if there are enough arguments
        if len(split_msg) == 4:
            target_contact = split_msg[1]
            days_str = split_msg[2]
            unit = split_msg[3]
            time_frame = f"{days_str}{unit}"
        else:
            return Chatbot.languages.get_stats_usage_err(  # type: ignore [union-attr]
                sender_lang)
        target_contact_key = f"whatsapp:{target_contact}"  # specified user
        if target_contact_key not in self.subscribers:
            return Chatbot.languages.get_unfound_err(  # type: ignore [union-attr]
                sender_lang)
        # Check if the time frame is valid
        pattern = r"(\d+)\s*(\w+)"
        match = re.match(pattern, time_frame)
        if match:
            days, unit = int(match.group(1)), match.group(2)
            if unit not in ("day", "days"):
                return Chatbot.languages.get_stats_err(  # type: ignore [union-attr]
                    sender_lang)
        else:
            return Chatbot.languages.get_stats_err(  # type: ignore [union-attr]
                sender_lang)
        # Calculate the start and end dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        # Tally timestamps
        message_count = 0
        for timestamp_str in self.logs[target_contact_key]["timestamps"]:
            timestamp = datetime.fromisoformat(timestamp_str)
            if start_date <= timestamp <= end_date:
                message_count += 1
        # TODO: convert to a translated success message
        return f"User {target_contact} sent {message_count} messages."

    # TODO: target_user should work as both username and phone number
    def _get_last_post_time(
            self,
            user_contact: str,
            target_user: str = "") -> str:
        """Get the latest post's timestamp for one or all users.

        Arguments:
            user_contact -- the WhatsApp contact info of the user making this
                request (if target_user is not provided, check timestamp for
                this user)

        Keyword Arguments:
            target_user -- a user to get a timestamp for (default: {""})

        Returns:
            the date that the user in question last sent a message.
        """
        sender_lang = self.subscribers[user_contact]["lang"]
        target_user = target_user.strip().lower()

        if target_user != "":
            # Check if target_user is a name, then get the corresponding phone
            # number
            for contact, user_info in self.subscribers.items():
                if user_info["name"].lower() == target_user or \
                        contact.split(":")[1].lower() == target_user:
                    target_user = contact.split(":")[1]
                    target_name = user_info["name"]
                    break
            else:
                return Chatbot.languages.get_unfound_err(  # type: ignore [union-attr]
                    sender_lang)

            user_to_check = f"whatsapp:{target_user}"
            if user_to_check not in self.logs:
                return Chatbot.languages.get_unfound_err(  # type: ignore [union-attr]
                    sender_lang)
            timestamps = self.logs[user_to_check]["timestamps"]
            if not timestamps:
                # TODO: convert to a translated error
                return f"User {target_name} ({target_user}) has not posted any messages yet."
            last_post_time = max(timestamps, key=datetime.fromisoformat)
            # TODO: convert to a translated success message
            return f"Last post for user {target_name} ({target_user}) was: {last_post_time}"
        else:
            last_posts = {}
            for user in self.logs:
                timestamps = self.logs[user]["timestamps"]
                if timestamps:
                    last_post_time = max(
                        timestamps, key=datetime.fromisoformat)
                    last_posts[user] = last_post_time
            if not last_posts:
                # TODO: convert to a translated error
                return "No messages have been posted yet."
            # TODO: convert to a translated success message
            last_post_messages = "\n".join(
                [
                    f"{self.subscribers[user]['name']} ({user.split(':')[1]}): {timestamp}" for user,
                    timestamp in last_posts.items()])
            return f"Last post for all users:\n{last_post_messages}"

    def _generate_total_stats(self, sender_contact: str, msg: str) -> str:
        """Generate message statistics for all users in a specified time frame.

        Arguments:
            sender_contact -- WhatsApp contact info of the sender
            msg -- the message sent to the bot, containing the time frame for
                statistics

        Returns:
            A string containing the total message statistics or an error message
                if the input is incorrect.
        """
        sender_lang = self.subscribers[sender_contact]["lang"]
        split_msg = msg.split()
        if len(split_msg) == 3:
            days_str = split_msg[1]
            unit = split_msg[2]
            time_frame = f"{days_str}{unit}"
        else:
            return Chatbot.languages.get_stats_usage_err(  # type: ignore [union-attr]
                sender_lang)
        # Check if the time frame is valid
        pattern = r"(\d+)\s*(\w+)"
        match = re.match(pattern, time_frame)
        if match:
            days, unit = int(match.group(1)), match.group(2)
            if unit not in ("day", "days"):
                return Chatbot.languages.get_stats_err(  # type: ignore [union-attr]
                    sender_lang)
        else:
            return Chatbot.languages.get_stats_err(  # type: ignore [union-attr]
                sender_lang)
        # Calculate the start and end dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        # Tally total messages
        total_message_count = 0
        for contact_key in self.logs:
            for timestamp_str in self.logs[contact_key]["timestamps"]:
                timestamp = datetime.fromisoformat(timestamp_str)
                if start_date <= timestamp <= end_date:
                    total_message_count += 1
        # TODO: convert to translated success message
        return f"Total messages sent by all users: {total_message_count}"

    def _list_subscribers(self) -> str:
        """Generate a formatted list of subscribers with their data.

        Returns:
            A formatted string representing the list of subscribers, including
            their name, phone number, language, and role. If there are no
            subscribers, a message indicating this will be returned.
        """
        # Check if there are any subscribers
        # TODO: convert to a translated error message
        if not self.subscribers:
            return "No subscribers found."

        # Initialize the formatted list with a header
        # TODO: convert to a translated success message
        formatted_list = "List of subscribers:\n\n"

        # Iterate through the subscribers and format their information
        # TODO: convert to a translated message
        for contact, user_info in self.subscribers.items():
            formatted_list += f"Name: {user_info['name']}\n"
            formatted_list += f"Number: {contact.split(':')[1]}\n"
            formatted_list += f"Language: {user_info['lang']}\n"
            formatted_list += f"Role: {user_info['role']}\n"
            formatted_list += "-" * 30 + "\n"

        # Return the formatted list of subscribers
        return formatted_list

    def process_msg(
            self,
            msg: str,
            sender_contact: str,
            media_urls: List[str]) -> str:
        """Process a bot command.

        Arguments:
            msg -- the message sent to the bot
            sender_contact -- the WhatsApp contact info of the sender
            media_urls -- a list of media URLs sent with the message, if any

        Returns:
            A string suitable for returning from a Flask route endpoint.
        """
        try:
            sender = self.subscribers[sender_contact]
            sender_name = sender["name"]
            role = sender["role"]
            sender_lang = sender["lang"]
        except KeyError:
            return ""  # ignore; they aren't subscribed
        if msg == "" and len(media_urls) == 0:
            return ""  # ignore; nothing to send

        # Store the timestamp if applicable
        self._store_message_timestamp(sender_contact, msg)

        # first word in message
        word_1 = msg.split()[0].lower() if msg != "" else ""

        # PM someone:
        if word_1[0:1] == pm_char:
            split = msg.split()  # don't convert first word to lowercase
            pm_name = split[0][1:]  # display name without PM character
            return self._reply(
                self._query(
                    " ".join(split[1:]),
                    sender_name,
                    sender_lang,
                    pm_name,
                    media_urls))

        # Message group or /test as user:
        elif role == consts.USER:
            if word_1 == consts.TEST:  # test translate
                return self._reply(self._test_translate(msg, sender_contact))
            elif word_1[0:1] == "/" and len(word_1) > 1:
                return ""  # ignore invalid/unauthorized command
            else:  # just send a message
                text = sender_name + " says:\n" + msg
                self._push(text, sender_contact, media_urls)
                return ""  # say nothing to sender

        # Message group or perform any slash command as admin or superuser:
        else:
            match word_1:
                case consts.TEST:  # test translate
                    return self._reply(
                        self._test_translate(
                            msg, sender_contact))
                case consts.ADD:  # add user to subscribers
                    return self._reply(
                        self._add_subscriber(
                            msg, sender_contact))
                case consts.REMOVE:  # remove user from subscribers
                    return self._reply(
                        self._remove_subscriber(
                            msg, sender_contact))
                case consts.LIST:  # list all subscribers with their data
                    return self._reply(self._list_subscribers())

                case consts.STATS:
                    stats = self._generate_stats(sender_contact, msg)
                    return self._reply(stats)
                case consts.LASTPOST:  # get last post time for user
                    target_user = msg.split()[1] if len(
                        msg.split()) > 1 else ""
                    return self._reply(
                        self._get_last_post_time(
                            sender_contact, target_user))
                case consts.TOTALSTATS:
                    total_stats = self._generate_total_stats(
                        sender_contact, msg)
                    return self._reply(total_stats)
                case _:  # just send a message
                    if word_1[0:1] == "/" and len(word_1) > 1:
                        return ""  # ignore invalid/unauthorized command
                    text = sender_name + " says:\n" + msg
                    return self._push(text, sender_contact, media_urls)


TWILIO_ACCOUNT_SID: str = os.getenv(
    "TWILIO_ACCOUNT_SID")  # type: ignore [assignment]
TWILIO_AUTH_TOKEN: str = os.getenv(
    "TWILIO_AUTH_TOKEN")  # type: ignore [assignment]
TWILIO_NUMBER: str = os.getenv("TWILIO_NUMBER")  # type: ignore [assignment]
mr_botty = Chatbot(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_NUMBER)
"""Global Chatbot object, of which there could theoretically be many."""
