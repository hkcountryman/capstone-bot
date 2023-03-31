# mypy: disable-error-code=import

"""Basic functionality for a WhatsApp chatbot.

This module contains the class definition to create Chatbot objects, each of
which can support one group of subscribers on WhatsApp.

It also contains the definition to create Polls, which are associated with a
Chatbot in a many to one relationship.

Lastly, it contains supporting classes for the Chatbot and Poll classes, namely
several TypedDicts and an asynchronous Timer class.
"""

import asyncio
import datetime as dt
import json
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, TypedDict
from uuid import UUID, uuid4

import requests
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from language_data import LangData, translate_to

consts = SimpleNamespace()
# Constant strings for bot commands
consts.TEST = "/test"  # test translate
consts.ADD = "/add"  # add user
consts.LIST = "/list"  # list all users
consts.POLL = "/poll"  # start a poll
consts.REMOVE = "/remove"  # remove user
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


class PollsInfo(TypedDict):
    """A TypedDict to describe a poll.

    For use as the values in a polls member of a Chatbot instance, the keys to
    which are to be strings of the unique ID for the particular poll.
    """
    due: str  # due date timestamp (YYYY-MM-DD HH:MM, 24-hour clock, UTC)
    question: str  # question to ask users
    num_votes: Dict[str, int]  # number of votes indexed by poll options
    user_votes: Dict[str, str]  # each user who voted and corresponding choice


class Chatbot:
    """The chatbot logic.

    Class variables:
        commands -- List of slash commands for the bot
        languages -- Data shared by all chatbots on the server about the
            languages supported by LibreTranslate

    Instance variables:
        twilio_account_sid -- Account SID for the Twilio account
        twilio_auth_token -- Twilio authorization token
        twilio_number -- Bot's registered Twilio number
        client -- Client with which to access the Twilio API
        number -- Phone number the bot texts from
        json_file -- Path to a JSON file containing subscriber data
        subscribers -- Dictionary containing the data loaded from the file
        polls -- Dictionary of ongoing polls indexed by unique IDs and stored
            in the file
        timers -- Collection of ongoing timer tasks

    Methods:
        message -- Push a message to a single recipient
        push -- Push a translated message and/or media to one or more recipients
        process_cmd -- Process a slash command and send a reply from the bot
    """
    commands = [
        consts.TEST,
        consts.ADD,
        consts.LIST,
        consts.POLL,
        consts.REMOVE]
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
        self.twilio_account_sid = account_sid
        self.twilio_auth_token = auth_token
        self.twilio_number = number
        self.client = Client(account_sid, auth_token)
        self.number = number
        self.json_file = json_file
        self.polls: Dict[UUID, Poll] = {}
        self.timers = set()
        with open(json_file, encoding="utf-8") as file:
            # TODO: fix self.subscribers to be json.load(file)["users"]
            self.subscribers: Dict[str, SubscribersInfo] = json.load(file)
            # TODO: fix self.polls to be json.load(file)["polls"]
            polls: Dict[str, PollsInfo] = json.load(file)
            for (uid, poll) in polls.items():
                # Add a Poll object to self.polls for each entry in JSON:
                new_poll = Poll(self,
                                poll["due"],
                                poll["question"],
                                list(poll["num_votes"].keys()),
                                poll["num_votes"],
                                poll["user_votes"],
                                UUID(uid))
                self.polls[UUID(uid)] = new_poll
                # Schedule a timer for each added Poll object:
                # NOTE: Since these were already in the JSON, they won't raise
                # a ValueError because they were already validated
                task = asyncio.create_task(new_poll.start_timer())
                self.timers.add(task)
                task.add_done_callback(self.timers.discard)

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

    def message(self, recipient: str, msg_body: str, media_urls: List[str]):
        """Push a message to a single recipient.

        Arguments:
            recipient -- WhatsApp contact info of the user to message
            msg_body -- Text of the message to send
            media_urls -- List of URLs for any media being sent
        """
        msg = self.client.messages.create(
            from_=f"whatsapp:{self.number}",
            to=recipient,
            body=msg_body,  # message text
            media_url=media_urls  # files
        )
        print(msg.sid)  # write the message to the stream

    def push(
            self,
            text: str,
            sender: str,
            media_urls: List[str]) -> str:
        """Push a translated message and/or media to one or more recipients.

        Arguments:
            text -- Contents of the message
            sender -- Sender's WhatsApp contact info
            media_urls -- List of URLs for any media being sent

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
                self.message(s, translated, media_urls)
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

    def _add_subscriber(self, msg: str, sender_contact: str) -> str:
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
                return Chatbot.languages.get_add_role_err(  # type: ignore [union-attr]
                    sender_lang)

            # Check if the language code is valid
            if new_lang not in\
                    Chatbot.languages.codes:  # type: ignore [union-attr]
                return Chatbot.languages.get_add_lang_err(  # type: ignore [union-attr]
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

    def _remove_subscriber(self, msg: str, sender_contact: str) -> str:
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
                with open(self.json_file, "w", encoding="utf-8") as f:  # TODO: locking mechanism
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

        if not msg and len(media_urls) == 0:
            return ""  # ignore; nothing to send

        word_1 = msg.split()[0].lower() if msg else ""

        if role == consts.USER:
            if word_1 == consts.TEST:  # test translate
                return self._reply(self._test_translate(msg, sender_contact))
            elif word_1[0:1] == "/" and len(word_1) > 1:
                return ""  # ignore invalid/unauthorized command
            else:  # just send a message
                text = sender_name + " says:\n" + msg
                self.push(text, sender_contact, media_urls)
                return ""  # say nothing to sender
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
                case consts.LIST:  # list all subscribers with their data
                    return self._reply(json.dumps(self.subscribers, indent=2))
                case consts.POLL:  # start a new poll
                    # TODO: make Poll and start Timer, make sure to handle
                    # ValueError and warn creator.
                    return self._reply("")
                case consts.REMOVE:  # remove user from subscribers
                    return self._reply(
                        self._remove_subscriber(
                            msg, sender_contact))
                case _:  # just send a message
                    if word_1[0:1] == "/" and len(word_1) > 1:
                        return ""  # ignore invalid/unauthorized command
                    text = sender_name + " says:\n" + msg
                    return self.push(text, sender_contact, media_urls)


class Timer:
    """An asynchronous timer based on https://stackoverflow.com/a/45430833.

    Methods:
        cancel -- Cancels the timer
    """

    def __init__(
            self,
            timeout: float,
            callback: Callable,
            cb_args: List[Any]):
        """Constructor.

        Arguments:
            timeout -- Time in seconds before timer goes off
            callback -- Function to execute when timer goes off
            cb_args -- List of arguments to pass to callback
        """
        self._timeout = timeout
        self._callback = callback
        self._cb_args = cb_args
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        """Wait for the timer to expire and then execute self._callback."""
        await asyncio.sleep(self._timeout)
        await self._callback(*self._cb_args)

    def cancel(self):
        """Cancel the timer."""
        self._task.cancel()


class Poll:
    """An object to represent a poll in a group chat.

    Instance variables:
        uid -- Unique ID for this poll
        bot -- Chatbot this poll belongs to
        due -- String description of a timestamp or time period
        question -- Question to ask users
        options -- All options users can pick from
        num_votes -- Options and their corresponding number of votes
        user_votes -- Users and their corresponding chosen options

    Methods:
        start_timer -- Asynchronous call after creating a new Poll object to
            start its timer
        vote -- Process an incoming vote from a subscriber
    """

    def __init__(self,
                 bot: Chatbot,
                 due: str,
                 question: str,
                 options: List[str],
                 num_votes: Dict[str, int] | None = None,
                 user_votes: Dict[str, str] | None = None,
                 uid: UUID | None = None):
        """Constructor.

        Arguments:
            bot -- Chatbot this poll belongs to
            due -- String description of a timestamp or time period
            question -- Question to ask users
            options -- All options users can pick from

        Keyword Arguments:
            num_votes -- Options and their corresponding number of votes, if
                this isn't a new poll (default: {None})
            user_votes -- Users and their corresponding chosen options, if this
                isn't a new poll (default: {None})
            uid -- Unique ID for this poll, if this isn't a new poll (default:
                {None})
        """
        self.uid = uuid4() if not uid else uid
        self.bot = bot
        self.due = due
        self.question = question
        self.options = options
        self.num_votes = {
            opt: 0 for opt in options} if not num_votes else num_votes
        self.user_votes = {} if not user_votes else user_votes
        if uid is None:  # creating a new poll; must write to JSON
            pass
            # TODO: Kevin, can you handle writing the JSON like this?
            # "polls": {
            #       "<str(poll.uid)>": {
            #           "due": <self.due>,
            #           "question": <poll.question>,
            #           "num_votes": <poll.num_votes>,
            #           "user_votes": <poll.user_votes>
            #       }
            # }

    async def start_timer(self):
        """Starts the asynchronous timer for this poll.

        Raises:
            ValueError: If parsing fails
        """
        try:
            seconds = self._calc_timer()
        except ValueError as e:  # parsing failed
            # Remove this poll from JSON file:
            # TODO: Kevin?
            # Remove reference to this Poll object from its Chatbot:
            self.bot.polls.pop(self.uid)
            raise ValueError from e
        Timer(seconds, self._publish_results, [self])

    def _calc_timer(self) -> float:
        """Calculates the duration of a timer.

        Returns:
            A float value representing the seconds into the future when the
                timer will end and a datetime to store in the JSON file.

        Raises:
            ValueError: If due cannot be parsed
        """
        now = dt.datetime.now(dt.UTC)
        if len(self.due.split()) == 2:  # datetimestamp; may raise ValueError
            due_date = dt.datetime.strptime(self.due, "%Y-%m-%d %H:%M")
            delta = due_date - now
        elif self.due[0] != "+":  # just timestamp; may raise ValueError
            due_date = dt.datetime.strptime(self.due, "%H:%M")
            delta = due_date - now
        elif self.due[0] == "+":  # time period
            hrs_mins = self.due[1:].split(":")
            if len(hrs_mins) != 2 or not hrs_mins[0].isdigit(
            ) or not hrs_mins[1].isdigit():
                raise ValueError
            delta = dt.timedelta(
                hours=int(hrs_mins[0]),
                minutes=int(hrs_mins[1]))
            due_date = now + delta
        else:
            raise ValueError  # parsing failed
        due_date = due_date.replace(tzinfo=dt.UTC)
        if due_date <= now:
            raise ValueError  # due in past
        else:
            return delta.total_seconds()

    async def _publish_results(self):
        """Send all subscribers the results of this poll and delete it."""
        results = ""  # TODO:
        self.bot.push(results, f"whatsapp:{self.bot.number}", [])
        self.bot.polls.pop(self.uid)  # remove from Chatbot object
        # TODO: Kevin: remove from self.bot.json_file

    def vote(self, user: str, choice_num: int):
        """Apply one user's vote, changing it if they already voted.

        Arguments:
            user -- WhatsApp contact info of the user voting
            choice_num -- Option number chosen (1-indexed)

        Raises:
            IndexError: If choice_num does not correspond to an option for this
                poll
        """
        option = self.options[choice_num - 1]  # adjust for 0-indexing
        if user in self.user_votes:  # already voted
            current_choice = self.user_votes[user]
            self.num_votes[current_choice] -= 1  # remove previous vote
        self.user_votes[user] = option  # set user's choice
        self.num_votes[option] += 1  # add their vote
