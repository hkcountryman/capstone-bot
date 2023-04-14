"""LibreTranslate language data.

This module contains information about languages supported by LibreTranslate. It
includes the LangData class, which can be shared by all chatbots on the server
to look up language names, codes, and error messages, as well as the
translate_to function, which can translate text into a target language.

Classes:
    LangEntry -- A TypedDict to describe all data associated with a language
        code, namely the human-readable name, translation target codes, and
        error and success messages translated into that language
    LangData -- A class containing convenience members for maintaining the
        LangEntry dictionaries for all supported languages, a list of all
        language codes, a list of all language names, and methods to return
        translated error and success messages

Functions:
    translate_to -- Translate some text to a given target language
"""

import json
import os
from types import SimpleNamespace
from typing import Dict, List, TypedDict

import requests


def _get_timeout() -> int:
    """Populate the timeout constant from the environment.

    Returns:
        The integer value of the environment variable TRANSLATION_TIMEOUT, or 5
            if the variable is nonnumeric or nonexistent.
    """
    try:
        return int(os.getenv("TRANSLATION_TIMEOUT"))  # type: ignore [arg-type]
    except (ValueError, TypeError):
        return 10


consts = SimpleNamespace()
consts.MIRRORS = [
    url + "translate" for url in os.getenv(  # list of mirrors
        "LIBRETRANSLATE").split()]  # type: ignore [union-attr]
consts.TIMEOUT = _get_timeout()  # seconds before requests time out

# Strings for use in error messages
err_msgs = SimpleNamespace()
err_msgs.example = "Example:\n"  # example to follow
err_msgs.test_example = "/test es How are you today?"  # /test example
err_msgs.lang_err = "Choose a valid language. "  # preface errors
err_msgs.lang_list = ""  # list of all valid languages
err_msgs.add_example = "/add +12345678900 xX_bob_Xx en user"  # /add example
# invalid phone number
err_msgs.add_phone_err = \
    "A phone number contains only digits and a plus sign for the country code."
err_msgs.add_name_err = "Choose a different username."  # display name taken
err_msgs.role_err = "Choose a valid role:"  # preface errors
err_msgs.roles = " (user | admin | super)"  # valid roles
err_msgs.exists_err = "User already exists."  # /add existing user
err_msgs.remove_example = "/remove +12345678900\n/remove username"  # /remove example
err_msgs.unfound_err = "User not found."  # remove nonexistent user
err_msgs.remove_self_err = "You cannot remove yourself."  # remove self
err_msgs.remove_super_err = "You cannot remove a superuser."  # admin removes super
# Invalid time frame
err_msgs.stats_err = "Invalid time frame. "
err_msgs.stats_usage_err = "/stats 1 day +12345678900\n/stats 7 days name\n/stats 30 days"
err_msgs.no_posts = "There are no messages."  # /lastpost no messages


# Strings for success messages
success = SimpleNamespace()
success.added = "New user added successfully."  # /add
success.removed = "User removed successfully."  # /remove
success.stats = ["user", "phone number", "messages"]  # /stats column headers
# /lastpost column headers
success.lastpost = ["user", "phone number", "most recent message"]
success.list_ = [
    "user",
    "phone number",
    "language",
    "type"]  # /list column headers


class LangEntry(TypedDict):
    """A TypedDict to describe associated data for some language code.

    The error and success messages should be initialized to empty strings and
    are saved as they are needed and subsequently translated into the language.
    """
    # Language data
    name: str  # human-readable name
    targets: List[str]  # codes for targets this language can be translated to

    # Errors
    example: str  # preface all examples with this
    test_example: str  # /test error message in this language
    lang_err: str  # generic error header for invalid languages in this language
    lang_list: str  # list of valid languages (no codes) in this language
    add_example: str  # /add example
    add_phone_err: str  # invalid phone number
    add_name_err: str  # display name taken
    role_err: str  # generic error header for invalid roles in this language
    add_role_err: str  # /add role error message in this language
    exists_err: str  # /add error if user exists
    remove_example: str  # /remove example
    unfound_err: str  # /remove error if user not found
    remove_self_err: str  # /remove error if user tries to remove self
    remove_super_err: str  # /remove error if admin tries to remove super
    stats_err: str  # /stats error if invalid time frame
    stats_usage_err: str  # /stats error if invalid usage
    no_posts: str  # /lastpost no messages

    # Success messages
    added: str  # /add
    removed: str  # /remove
    stats: str  # /stats column headers
    lastpost: str  # /lastpost column headers
    list_: str  # /list column headers


class LangData:
    """An object that can hold all language data.

    Language data includes human-readable names and translation targets
    associated with a language code as well as error messages.

    It also has methods to return error and success messages translated into a
    given language.

    Instance variables:
        codes -- List of all language codes supported by LibreTranslate
        names -- List of all human-readable language names supported by
            LibreTranslate
        entries -- Dictionary associating language codes with their
            corresponding LangEntry dictionaries

    Methods:
        get_test_example -- get the /test error message
        get_add_lang_err -- get the error message when /add uses an invalid
            language
        get_add_phone_err -- get the /add error message when a phone number is
            invalid
        get_add_name_err -- get the /add error message when a display name is
            already taken
        get_add_role_err -- get the /add error message when a role is invalid
        get_exists_err -- get the /add error message when attempting to add an
            existing user
        get_add_err -- get the generic /add error message for bad syntax
        get_add_success -- get a success message for /add
        get_unfound_err -- get an error message when referencing a nonexistent
            user
        get_remove_err -- get the generic /remove error message for bad syntax
        get_remove_self_err -- get the error message for removing yourself
        get_remove_super_err -- get the error message for removing a superuser
            as an admin
        get_remove_success -- get a success message for /remove
        get_stats_err -- get the error message for giving an invalid timeframe
            for /stats
        get_stats_usage_err -- get the generic /stats error message for bad
            syntax
        get_no_posts -- get an error message when calling /lastpost if there
            have been no posts
        get_stats_headers -- get the CSV headers for a /stats report
        get_lastpost_headers -- get the CSV headers for a /lastpost report
        get_list_headers -- get the CSV headers for a /list report
    """

    def __init__(self):
        # Attempt to populate an up-to-date language models list:
        idx = 0  # index in URLs
        res = None
        while res is None and idx < len(consts.MIRRORS):
            try:
                res = requests.get(
                    f"{consts.MIRRORS[idx]}languages",
                    timeout=consts.TIMEOUT)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                idx = idx + 1
        if res is not None and res.status_code == 200:
            languages = res.json()
        else:
            # If that failed, we can load the data from languages.json
            with open("languages.json", encoding="utf-8") as file:
                languages = json.load(file)
        self.codes: List[str] = []
        self.names: List[str] = []
        self.entries: Dict[str, LangEntry] = {}
        for lang in languages:
            self.codes.append(lang["code"])
            self.names.append(lang["name"])
            self.entries[lang["code"]] = {
                "name": lang["name"],
                "targets": lang["targets"],
                "example": "",
                "test_example": "",
                "lang_err": "",
                "lang_list": "",
                "add_example": "",
                "add_phone_err": "",
                "add_name_err": "",
                "role_err": "",
                "add_role_err": "",
                "exists_err": "",
                "remove_example": "",
                "unfound_err": "",
                "remove_self_err": "",
                "remove_super_err": "",
                "stats_err": "",
                "stats_usage_err": "",
                "no_posts": "",
                "added": "",
                "removed": "",
                "stats": "",
                "lastpost": "",
                "list_": ""}
        err_msgs.lang_list = "".join(
            ["Languages:"] + list(map(lambda l: (f"\n{l}"), self.names)))

    # Example commands

    def _get_example(self, code: str) -> str:
        """Get a translated generic error header for invalid languages.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.

        Raises:
            TimeoutError -- If all mirrors time out before providing a
                translation
            requests.ConnectionError -- if all mirrors are down
            requests.HTTPError -- If a non-OK response is received from the
                LibreTranslate API
        """
        if self.entries[code]["example"] == "":
            self.entries[code]["example"] = translate_to(
                err_msgs.example, code)
        return self.entries[code]["example"]

    # Invalid languages

    def _get_lang_list(self, code: str) -> str:
        """Get a translated list of valid languages with their codes.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.

        Raises:
            TimeoutError -- If all mirrors time out before providing a
                translation
            requests.ConnectionError -- if all mirrors are down
            requests.HTTPError -- If a non-OK response is received from the
                LibreTranslate API
        """
        if self.entries[code]["lang_list"] == "":
            # First get translated list of valid languages without the codes:
            no_codes = translate_to(err_msgs.lang_list, code).split("\n")
            # Then add the codes:
            self.entries[code]["lang_list"] = "".join(
                no_codes[0:1] + [
                    f"\n{self.codes[i]} ({l})" for i, l in enumerate(
                        no_codes[1:])])
        return self.entries[code]["lang_list"]

    def _get_lang_err(self, code: str) -> str:
        """Get a translated generic error header for invalid languages.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.

        Raises:
            TimeoutError -- If all mirrors time out before providing a
                translation
            requests.ConnectionError -- if all mirrors are down
            requests.HTTPError -- If a non-OK response is received from the
                LibreTranslate API
        """
        if self.entries[code]["lang_err"] == "":
            self.entries[code]["lang_err"] = translate_to(
                err_msgs.lang_err, code)
        return self.entries[code]["lang_err"]

    # /test

    def get_test_example(self, code: str) -> str:
        """Get a translated error when /test command is invalid.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["test_example"] == "":
            try:
                self.entries[code]["test_example"] = self._get_lang_err(
                    code) + self._get_example(code) + err_msgs.test_example + \
                    "\n\n" + self._get_lang_list(code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.lang_err + err_msgs.example + \
                    err_msgs.test_example + "\n\n" + err_msgs.lang_list
        return self.entries[code]["test_example"]

    # /add

    def get_add_lang_err(self, code: str) -> str:
        """Get a translated error when /add command uses an invalid language.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["add_example"] == "":
            try:
                self.entries[code]["add_example"] = self._get_lang_err(
                    code) + self._get_example(code) + err_msgs.add_example + \
                    "\n\n" + self._get_lang_list(code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.lang_err + err_msgs.example + \
                    err_msgs.add_example + "\n\n" + err_msgs.lang_list
        return self.entries[code]["add_example"]

    def get_add_phone_err(self, code: str) -> str:
        """Get a translated error when a phone number is invalid.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["add_phone_err"] == "":
            try:
                self.entries[code]["add_phone_err"] = translate_to(
                    err_msgs.add_phone_err, code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.add_phone_err
        return self.entries[code]["add_phone_err"]

    def get_add_name_err(self, code: str) -> str:
        """Get a translated error when a display name is taken.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["add_name_err"] == "":
            try:
                self.entries[code]["add_name_err"] = translate_to(
                    err_msgs.add_name_err, code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.add_name_err
        return self.entries[code]["add_name_err"]

    def _get_role_err(self, code: str) -> str:
        """Get a translated error when a role is invalid.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.

        Raises:
            TimeoutError -- If all mirrors time out before providing a
                translation
            requests.ConnectionError -- if all mirrors are down
            requests.HTTPError -- If a non-OK response is received from the
                LibreTranslate API
        """
        if self.entries[code]["role_err"] == "":
            self.entries[code]["role_err"] = translate_to(
                err_msgs.role_err, code)
        return self.entries[code]["role_err"]

    def get_add_role_err(self, code: str) -> str:
        """Get a translated error when a role is invalid + list of valid roles.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["add_role_err"] == "":
            try:
                self.entries[code]["add_role_err"] = self._get_role_err(
                    code) + err_msgs.roles + "\n" + self._get_example(code) + \
                    err_msgs.add_example
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.role_err + err_msgs.roles + "\n" + \
                    err_msgs.example + err_msgs.add_example
        return self.entries[code]["add_role_err"]

    def get_exists_err(self, code: str) -> str:
        """Get a translated error when an added user already exists.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["exists_err"] == "":
            try:
                self.entries[code]["exists_err"] = translate_to(
                    err_msgs.exists_err, code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.exists_err
        return self.entries[code]["exists_err"]

    def get_add_err(self, code: str) -> str:
        """Get a translated error when /add command is invalid.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["add_example"] == "":
            try:
                self.entries[code]["add_example"] = self._get_example(code) + \
                    err_msgs.add_example
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.example + err_msgs.add_example
        return self.entries[code]["add_example"]

    def get_add_success(self, code: str) -> str:
        """Get a translated success message upon adding a user.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["added"] == "":
            try:
                self.entries[code]["added"] = translate_to(
                    success.added, code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the message at the moment, compromise
                # and return it in English
                return success.added
        return self.entries[code]["added"]

    # /remove

    def get_unfound_err(self, code: str) -> str:
        """Get a translated error when referencing a nonexistent user.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["unfound_err"] == "":
            try:
                self.entries[code]["unfound_err"] = translate_to(
                    err_msgs.unfound_err, code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.unfound_err
        return self.entries[code]["unfound_err"]

    def get_remove_err(self, code: str) -> str:
        """Get a translated error when calling /remove with improper syntax.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["remove_example"] == "":
            try:
                self.entries[code]["remove_example"] = self._get_example(
                    code) + err_msgs.remove_example
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.example + err_msgs.remove_example
        return self.entries[code]["remove_example"]

    def get_remove_self_err(self, code: str) -> str:
        """Get a translated error when calling /remove on yourself.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["remove_self_err"] == "":
            try:
                self.entries[code]["remove_self_err"] = translate_to(
                    err_msgs.remove_self_err, code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.remove_self_err
        return self.entries[code]["remove_self_err"]

    def get_remove_super_err(self, code: str) -> str:
        """Get a translated error when an admin calls /remove on a superuser.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["remove_super_err"] == "":
            try:
                self.entries[code]["remove_super_err"] = translate_to(
                    err_msgs.remove_super_err, code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.remove_super_err
        return self.entries[code]["remove_super_err"]

    def get_remove_success(self, code: str) -> str:
        """Get a translated success message upon removing a user.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["removed"] == "":
            try:
                self.entries[code]["removed"] = translate_to(
                    success.removed, code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the message at the moment, compromise
                # and return it in English
                return success.removed
        return self.entries[code]["removed"]

    # /stats

    def get_stats_err(self, code: str) -> str:
        """Get a translated error message for an invalid timeframes for /stats.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["stats_err"] == "":
            try:
                self.entries[code]["stats_err"] = translate_to(
                    err_msgs.stats_err, code) + self._get_example(code) + \
                    err_msgs.stats_usage_err
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.stats_err + err_msgs.example + \
                    err_msgs.stats_usage_err
        return self.entries[code]["stats_err"]

    def get_stats_usage_err(self, code: str) -> str:
        """Get a translated error message for bad syntax for the /stats command.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["stats_usage_err"] == "":
            try:
                self.entries[code]["stats_usage_err"] = self._get_example(
                    code) + err_msgs.stats_usage_err
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.stats_usage_err
        return self.entries[code]["stats_usage_err"]

    def get_no_posts(self, code: str) -> str:
        """Get a translated error message for /lastpost when there are no posts.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["no_posts"] == "":
            try:
                self.entries[code]["no_posts"] = translate_to(
                    err_msgs.no_posts, code)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return err_msgs.no_posts
        return self.entries[code]["no_posts"]

    def get_stats_headers(self, code: str) -> str:
        """Get translated column headers for the /stats report.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["stats"] == "":
            try:
                translated = [translate_to(x, code) for x in success.stats]
                self.entries[code]["stats"] = ", ".join(translated)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return ", ".join(success.stats)
        return self.entries[code]["stats"]

    def get_lastpost_headers(self, code: str) -> str:
        """Get translated column headers for the /lastpost report.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["lastpost"] == "":
            try:
                translated = [translate_to(x, code) for x in success.lastpost]
                self.entries[code]["lastpost"] = ", ".join(translated)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return ", ".join(success.lastpost)
        return self.entries[code]["lastpost"]

    def get_list_headers(self, code: str) -> str:
        """Get translated column headers for the /list report.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.
        """
        if self.entries[code]["list_"] == "":
            try:
                translated = [translate_to(x, code) for x in success.list_]
                self.entries[code]["list_"] = ", ".join(translated)
            except (TimeoutError, requests.ReadTimeout,
                    requests.ConnectionError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return ", ".join(success.list_)
        return self.entries[code]["list_"]


def translate_to(text: str, target_lang: str) -> str:
    """Translate text to the target language using the LibreTranslate API.

    Arguments:
        text -- Text to be translated
        target_lang -- Target language code ("en", "es", "fr", etc.)

    Returns:
        Translated text.

    Raises:
        TimeoutError -- If all mirrors time out before providing a translation
        requests.ConnectionError -- if all mirrors are down
        requests.HTTPError -- If a non-OK response is received from the
            LibreTranslate API
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
        except (TimeoutError, requests.ReadTimeout):
            idx = idx + 1
    if res is None:  # ran out of mirrors to try
        raise TimeoutError("Translation timed out for all mirrors")
    elif res.status_code == 200:
        return res.json()["translatedText"]
    else:
        raise requests.HTTPError(
            f"Translation failed: HTTP {res.status_code} {res.reason}")
