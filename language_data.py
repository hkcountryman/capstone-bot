"""LibreTranslate language data.

This module contains information about languages supported by LibreTranslate. It
includes the LangData class, which can be shared by all chatbots on the server
to look up language names, codes, and error messages, as well as the
translate_to function, which can translate text into a target language.
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
        return 5


consts = SimpleNamespace()
consts.MIRRORS = [
    url + "translate" for url in os.getenv(  # list of mirrors
        "LIBRETRANSLATE").split()]  # type: ignore [union-attr]
consts.TIMEOUT = _get_timeout()  # seconds before requests time out

# Strings for use in error messages
error_messages = SimpleNamespace()
error_messages.lang_err = "Choose a valid language. Example:"  # preface errors
error_messages.test_err = "\n/test es How are you today?\n\n"  # /test example
error_messages.lang_list = ""  # list of all valid languages


class LangEntry(TypedDict):
    """A TypedDict to describe associated data for some language code."""
    name: str  # human-readable name
    targets: List[str]  # codes for targets this language can be translated to
    lang_list: str | None  # list of valid languages in this language
    lang_err: str | None  # generic error header in this language
    test_err: str | None  # /test error message in this language


class LangData:
    """An object that can hold all language data.

    Language data includes human-readable names and translation targets
    associated with a language code as well as error messages

    Instance variables:
        codes -- List of all language codes supported by LibreTranslate
        names -- List of all human-readable language names supported by
            LibreTranslate
        entries -- Dictionary associating language codes with their
            corresponding LangEntry dictionaries

    Methods:
        get_test_err -- get the test error message for a given language code
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
            except TimeoutError:
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
                "lang_list": None,
                "lang_err": None,
                "test_err": None}
        error_messages.lang_list = "".join(
            ["Languages:"] + list(map(lambda l: (f"\n{l}"), self.names)))

    def _get_lang_list(self, code: str) -> str:
        """Get a translated list of valid languages with their codes.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.

        Raises:
            TimeoutError -- If all mirrors time out before providing a
                translation
            HTTPError -- If a non-OK response is received from the
                LibreTranslate API
        """
        if self.entries[code]["lang_list"] is None:
            # First get translated list of valid languages without the codes:
            no_codes = translate_to(error_messages.lang_list, code).split("\n")
            # Then add the codes:
            self.entries[code]["lang_list"] = "".join(
                no_codes[0:1] + [
                    f"\n{self.codes[i]} ({l})" for i, l in enumerate(
                        no_codes[1:])])
        return self.entries[code]["lang_list"]  # type: ignore [return-value]

    def _get_lang_err(self, code: str) -> str:
        """Get a translated generic error header.

        Arguments:
            code -- Code of the language to translate the output to

        Returns:
            The translated output.

        Raises:
            TimeoutError -- If all mirrors time out before providing a
                translation
            HTTPError -- If a non-OK response is received from the
                LibreTranslate API
        """
        if self.entries[code]["lang_err"] is None:
            self.entries[code]["lang_err"] = translate_to(
                error_messages.lang_err, code)
        return self.entries[code]["lang_err"]  # type: ignore [return-value]

    def get_test_err(self, code: str) -> str:
        if self.entries[code]["test_err"] is None:
            try:
                self.entries[code]["test_err"] = self._get_lang_err(
                    code) + error_messages.test_err + self._get_lang_list(code)
            except (TimeoutError, requests.HTTPError):
                # If we can't translate the error at the moment, compromise and
                # return it in English
                return error_messages.lang_err + error_messages.test_err + \
                    error_messages.lang_list
        return self.entries[code]["test_err"]  # type: ignore [return-value]


def translate_to(text: str, target_lang: str) -> str:
    """Translate text to the target language using the LibreTranslate API.

    Arguments:
        text -- Text to be translated
        target_lang -- Target language code ("en", "es", "fr", etc.)

    Returns:
        Translated text.

    Raises:
        TimeoutError -- If all mirrors time out before providing a translation
        HTTPError -- If a non-OK response is received from the LibreTranslate
            API
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
        raise TimeoutError("Translation timed out for all mirrors")
    elif res.status_code == 200:
        return res.json()["translatedText"]
    else:
        raise requests.HTTPError(
            f"Translation failed: HTTP {res.status_code} {res.reason}")
