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
import asyncio
import aiofiles
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
consts.LIST = "/list"  # list all users
consts.STATS = "/stats"  # get stats for user
consts.LASTPOST = "/lastpost"  # get last post for user

# Roles for users in JSON file
consts.USER = "user"  # can only execute test translation command
consts.ADMIN = "admin"  # can execute all slash commands but cannot remove super
consts.SUPER = "super"  # can execute all slash commands, no limits
consts.VALID_ROLES = [consts.USER, consts.ADMIN, consts.SUPER]

consts.API_OFFLINE = "LibreTranslate offline"  # LibreTranslate down error

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
        backup_file -- Path to a JSON file containing backup data for the
            subscribers JSON file
        key_file -- Path to a file containing the encryption key
        logs_file -- Path to a JSON file containing logs data
        backup_logs_file -- Path to a JSON file containing backup data for the
            logs JSON file
        logs_key_file -- Path to a file containing the encryption key for the
            logs JSON file
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
        consts.LIST,
        consts.STATS,
        consts.LASTPOST]
    """All slash commands for the bot."""

    languages: LangData | None = None
    """Data for all languages supported by LibreTranslate."""

    def __init__(
            self,
            account_sid: str,
            auth_token: str,
            number: str,
            json_file: str = "subscribers.json",
            backup_file: str = "subscribers_bak.json",
            key_file: str = "subscribers_key.key",
            logs_file: str = "logs.json",
            backup_logs_file: str = "logs_bak.json",
            logs_key_file: str = "logs_key.key"):
        """Create the ChatBot object and populate class members as needed.

        Arguments:
            account_sid -- Account SID
            auth_token -- Account auth token
            number -- Phone number the bot texts from, including country
                extension

        Keyword Arguments:
            json_file -- Path to a JSON file containing subscriber data
                (default: {"subscribers.json"})
            backup_file -- Path to a JSON file containing backup data for the
                above JSON file (default: {"subscribers_bak.json"})
            key_file -- Path to a file containing the encryption key (default:
                {"subscribers_key.json"})
            logs_file -- Path to a JSON file containing logs data (default:
                {"logs.json"})
            backup_logs_file -- Path to a JSON file containing backup data for
                the above JSON file (default: {"logs_bak.json"})
            logs_key_file -- Path to a file containing the encryption key for
                the logs JSON file (default: {"logs_key.json"})
        """
        if Chatbot.languages is None:
            Chatbot.languages = LangData()
        self.client = Client(account_sid, auth_token)
        self.number = number
        self.json_file = f"json/{json_file}"
        self.backup_file = f"json/{backup_file}"
        self.key_file = f"json/{key_file}"
        self.logs_file = f"json/{logs_file}"
        self.backup_logs_file = f"json/{backup_logs_file}"
        self.logs_key_file = f"json/{logs_key_file}"
        self.twilio_account_sid = account_sid
        self.twilio_auth_token = auth_token
        self.twilio_number = number

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
            # Print message to server logs file that original file is
            # corrupted...recent data may not have been saved.
            with open("server_log.txt", "a") as file:
                timestamp = datetime.now().strftime("%Y-%m-%d")
                file.write(
                    timestamp +
                    ": Corrupted subscribers.json file...using backup file. Newest data may be missing.\n")

            with open(self.backup_file, "rb") as file:
                backup_encrypted_data = file.read()
            backup_unencrypted_data = f.decrypt(
                backup_encrypted_data).decode("utf-8")
            self.subscribers = json.loads(backup_unencrypted_data)
        self.display_names: Dict[str, str] = {
            v["name"]: k for k, v in self.subscribers.items()}

        with open(self.logs_file, "rb") as file:
            encrypted_logs_data = file.read()
        with open(self.logs_key_file, "rb") as file:
            self.key2 = file.read()  # Retrieve encryption key
        f = Fernet(self.key2)
        try:
            unencrypted_logs_data = f.decrypt(
                encrypted_logs_data).decode("utf-8")
            # Put unecrypted data into dictionary
            self.logs = json.loads(unencrypted_logs_data)
        except BaseException:  # pylint: disable=broad-exception-caught
            # Handle corrupted file
            # Print message to server logs file that original file is
            # corrupted...recent data may not have been saved.
            with open("server_log.txt", "a") as file:
                timestamp = datetime.now().strftime("%Y-%m-%d")
                file.write(
                    timestamp +
                    ": Corrupted logs.json file...using backup file. Latest logs may be missing.\n")

            with open(self.backup_logs_file, "rb") as file:
                backup_encrypted_logs_data = file.read()
            backup_unencrypted_logs_data = f.decrypt(
                backup_encrypted_logs_data).decode("utf-8")
            # TODO: Put unecrypted data into dictionary
            self.logs = json.loads(backup_unencrypted_logs_data)

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
                    except (TimeoutError, requests.ReadTimeout,
                            requests.ConnectionError, requests.HTTPError):
                        return consts.API_OFFLINE
                    translations[self.subscribers[s]["lang"]] = translated
                msg = self.client.messages.create(
                    from_=f"whatsapp:{self.number}",
                    to=s,
                    body=translated,
                    media_url=media_urls)
                print(msg.sid)
        return ""

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
            recipient -- recipient display name or phone number with country
                code
            media_urls -- any attached media URLs from Twilio's CDN

        Returns:
            An empty string to the sender, or else an error message if the
                request to the LibreTranslate API times out or has some other
                error.
        """
        if not (msg == "" and len(media_urls) == 0):  # something to send
            # Check if recipient exists
            r = self.display_names.get(recipient, "")
            if r == "":  # not a display name; check if it's a phone number
                if f"whatsapp:{recipient}" not in self.subscribers:  # nope
                    return Chatbot.languages.get_unfound_err(  # type: ignore [union-attr]
                        sender_lang)
                else:  # is number
                    r = f"whatsapp:{recipient}"
            # Send message
            recipient_lang = self.subscribers[r]["lang"]
            text = f"Private message from {sender}:\n{msg}"
            try:
                translated = translate_to(text, recipient_lang)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                return consts.API_OFFLINE
            pm = self.client.messages.create(
                from_=f"whatsapp:{self.number}",
                to=r,
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
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                return consts.API_OFFLINE
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
            # Check if the display name is untaken and valid
            if new_name in self.display_names or new_name.startswith(
                    "whatsapp:"):
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

            # Save the updated subscribers to subscribers.json
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

    def _remove_subscriber(self, msg: str, sender_contact: str) -> str:
        """Remove a subscriber from the dictionary and save the dictionary
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
            user_contact = parts[1]  # user to attempt to remove
            # Check if user exists
            user_contact = self.display_names.get(parts[1], "")
            if user_contact == "":  # not a display name; check if it's a number
                if f"whatsapp:{parts[1]}" not in self.subscribers:  # nope
                    return Chatbot.languages.get_unfound_err(  # type: ignore [union-attr]
                        sender_lang)
                else:  # is number
                    user_contact = f"whatsapp:{parts[1]}"
            # Prevent sender from removing themselves
            if user_contact == sender_contact:
                return Chatbot.languages.get_remove_self_err(  # type: ignore [union-attr]
                    sender_lang)
            # Check if the sender has the necessary privileges
            if sender_role == consts.ADMIN and self.subscribers[
                    user_contact]["role"] == consts.SUPER:
                return Chatbot.languages.get_remove_super_err(  # type: ignore [union-attr]
                    sender_lang)
            else:
                name = self.subscribers[user_contact]["name"]
                del self.display_names[name]
                del self.subscribers[user_contact]

            # Save the updated subscribers to subscribers.json
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
            if sender_contact in self.logs:  # sender is already in the log file...
                if timestamp in self.logs[sender_contact]:
                    self.logs[sender_contact][timestamp] += 1
                else:
                    self.logs[sender_contact][timestamp] = 1
            else:  # otherwise, add them to logs before adding timestamp
                self.logs[sender_contact] = {timestamp: 1}

            # Remove messages older than 1 year
            one_year_ago = datetime.now() - timedelta(days=365)
            for contact_key in self.logs:
                self.logs[contact_key] = {
                    ts: count for ts, count in self.logs[contact_key].items() if
                    datetime.fromisoformat(ts) >= one_year_ago}

            # Save the updated logs to logs.json
            # Convert the logs dictionary to a formatted JSON string
            logs_list = json.dumps(self.logs, indent=4)
            # Create byte version of JSON string
            logs_list_byte = logs_list.encode("utf-8")
            f = Fernet(self.key2)
            encrypted_logs_data = f.encrypt(logs_list_byte)
            with open(self.logs_file, "wb") as file:
                file.write(encrypted_logs_data)
            # Copy data to backup file
            with open(self.logs_file, "rb") as fileone, \
                    open(self.backup_logs_file, "wb") as filetwo:
                for line in fileone:
                    filetwo.write(line)

    def _generate_stats(self, sender_contact: str, msg: str) -> str:
        """Generate message statistics for one or all users.

        Arguments:
            sender_contact -- WhatsApp contact info of the sender
            msg -- the message sent to the bot, containing the user contact,
                and the time frame for statistics

        Returns:
            A string containing the message statistics or an error message
                if the input is incorrect or the user is not found.
        """
        sender_lang = self.subscribers[sender_contact]["lang"]
        split_msg = msg.split()  # Check if there are enough arguments
        if len(split_msg) in (3, 4):
            days_str = split_msg[1]
            unit = split_msg[2]
            if len(split_msg) == 4:  # specific user
                target_contact = self.display_names.get(split_msg[3], "")
                target_name = split_msg[3]
                if target_contact == "":  # not a display name, check if it's a number
                    if f"whatsapp:{split_msg[3]}" not in self.subscribers:  # nope
                        return Chatbot.languages.get_unfound_err(  # type: ignore [union-attr]
                            sender_lang)
                    else:  # is number
                        target_contact = f"whatsapp:{split_msg[3]}"
                        target_name = self.subscribers[target_contact]["name"]
            else:
                target_contact = ""
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
        report = Chatbot.languages.get_stats_headers(  # type: ignore [union-attr]
            sender_lang)  # report to return
        # Tally timestamps for a specific user
        if target_contact != "":
            message_count = 0
            for timestamp_str, count in self.logs[target_contact].items():
                timestamp = datetime.fromisoformat(timestamp_str)
                if start_date <= timestamp <= end_date:
                    message_count += count
            phone = target_contact.split(":")[1]
            report += f"\n{target_name}, {phone}, {message_count}"
        # Tally total messages for all users
        else:
            total_message_count = 0
            for contact_key in self.logs:
                name = self.subscribers[contact_key]["name"]
                phone = contact_key.split(":")[1]
                user_message_count = 0
                for timestamp_str in self.logs[contact_key]:
                    # TODO: above will be self.logs[contact_key].keys()
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if start_date <= timestamp <= end_date:
                        total_message_count += 1
                        user_message_count += 1
                report += f"\n{name}, {phone}, {user_message_count}"
            report += f"\n,,{total_message_count}"  # sum
        # Return report
        return report

    def _get_last_post_time(
            self,
            user_contact: str,
            target_user: str = "") -> str:
        """Get the latest post's timestamp for one or all users.

        Arguments:
            user_contact -- the WhatsApp contact info of the user making this
                request (if target_user is not provided, check timestamp for
                the user invoking the request)

        Keyword Arguments:
            target_user -- a user to get a timestamp for (default: {""})

        Returns:
            the date that the user in question last sent a message.
        """
        sender_lang = self.subscribers[user_contact]["lang"]
        report = Chatbot.languages.get_lastpost_headers(  # type: ignore [union-attr]
            sender_lang)  # report to return
        # Specific user
        if target_user != "":
            # Check if recipient exists
            target_number = self.display_names.get(target_user, "")
            if target_number == "":  # not a display name; check if it's a phone number
                if f"whatsapp:{target_user}" not in self.subscribers:  # nope
                    return Chatbot.languages.get_unfound_err(  # type: ignore [union-attr]
                        sender_lang)
                else:  # is number
                    target_number = f"whatsapp:{target_user}"
                    target_name = self.subscribers[target_number]["name"]
            else:  # was a display name
                target_name = target_user
            # Locate user's timestamps
            phone = target_number.split(":")[1]  # remove "whatsapp:"
            timestamps = self.logs[target_number]
            # TODO: the above will change to self.logs[target_number], an
            # object with keys that are dates and values that are messages sent
            # on that date. All users should have an entry.
            if len(timestamps) == 0:
                return Chatbot.languages.get_no_posts(sender_lang)
            last_post_time = max(timestamps, key=datetime.fromisoformat)
            report += f"\n{target_name}, {phone}, {last_post_time}"
        # All users
        else:
            last_posts = {}
            for user, user_logs in self.logs.items():
                # TODO: the above will change to self.logs[user], an
                # object with keys that are dates and values that are messages
                # sent on that date. All users should have an entry.
                if len(user_logs) != 0:
                    name = self.subscribers[user]["name"]
                    last_post_time = max(user_logs, key=datetime.fromisoformat)
                    last_posts[user] = f"\n{name}, {user}, {last_post_time}"
            if not last_posts:
                return Chatbot.languages.get_no_posts(sender_lang)
            report += "".join(last_posts)
        # Return report
        return report

    def _list_subscribers(self, sender: str) -> str:
        """Generate a formatted list of subscribers with their data.

        Arguments:
            sender -- the WhatsApp contact info of the sender

        Returns:
            A formatted string representing the list of subscribers, including
            their name, phone number, language, and role.
        """
        sender_lang = self.subscribers[sender]["lang"]
        report = Chatbot.languages.get_list_headers(  # type: ignore [union-attr]
            sender_lang)
        # Iterate through the subscribers and format their information
        for contact, user_info in self.subscribers.items():
            name = user_info["name"]
            phone = contact.split(":")[1]
            lang = user_info["lang"]
            role = user_info["role"]
            report += f"\n{name}, {phone}, {lang}, {role}"
        # Return the formatted list of subscribers
        return report

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
                    return self._reply(self._list_subscribers(sender_contact))
                case consts.STATS:
                    stats = self._generate_stats(sender_contact, msg)
                    return self._reply(stats)
                case consts.LASTPOST:  # get last post time for user
                    target_user = msg.split()[1] if len(
                        msg.split()) > 1 else ""
                    return self._reply(
                        self._get_last_post_time(
                            sender_contact, target_user))
                case _:  # just send a message
                    if word_1[0:1] == "/" and len(word_1) > 1:
                        return ""  # ignore invalid/unauthorized command
                    text = sender_name + " says:\n" + msg
                    return self._push(text, sender_contact, media_urls)


# Create bot (keyword args not provided because they have defaults)
TWILIO_ACCOUNT_SID: str = os.getenv(
    "TWILIO_ACCOUNT_SID")  # type: ignore [assignment]
TWILIO_AUTH_TOKEN: str = os.getenv(
    "TWILIO_AUTH_TOKEN")  # type: ignore [assignment]
TWILIO_NUMBER: str = os.getenv("TWILIO_NUMBER")  # type: ignore [assignment]
mr_botty = Chatbot(
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_NUMBER)
"""Global Chatbot object, of which there could theoretically be many."""
