"""Necessary JSON setup for Chatbot usage.

This is a basic Python script to be run to set-up the JSON file storing user
data to be used for all of the included Chatbot functionality.
"""

import json
import os
import sys

from cryptography.fernet import Fernet  # type: ignore [import]

# Term color codes
RED = "\033[1;31m"
BOLD = "\033[;1m"
RESET = "\033[0;0m"


def usage():
    """Print a usage statement."""
    print("USAGE:")
    sys.stdout.write(BOLD)
    print(f"    {sys.argv[0]}", end="")
    sys.stdout.write(RESET)
    print(" [JSON file name]")


# Get JSON file name
try:
    file_name = sys.argv[1]
except IndexError:
    usage()
    sys.exit(1)
if not file_name.endswith(".json"):
    file_name = file_name + ".json"

print("Setting up user data file...\n")

# Get superuser phone number
sys.stdout.write(BOLD)
print("Enter your WhatsApp phone number (include country code): ", end="")
sys.stdout.write(RESET)
phone_number = input()

# Get superuser preferred language
with open("languages.json", "r", encoding="utf-8") as file:
    lang_json = [{"name": lang["name"], "code": lang["code"]}
                 for lang in json.load(file)]
lang_field_len = 20
num_spaces = lang_field_len - len("LANGUAGE")
sys.stdout.write(BOLD)
print("\nCODE LANGUAGE" + (" " * num_spaces) + "CODE LANGUAGE")
sys.stdout.write(RESET)
col_1 = lang_json[0:len(lang_json) // 2]
col_2 = lang_json[len(lang_json) // 2:]
for (i, lang) in enumerate(col_1):
    left = f"{lang['code']}   {lang['name'].ljust(lang_field_len)}"
    right = f"{col_2[i]['code']}   {col_2[i]['name']}"
    print(f"{left}{right}")
language = ""
sys.stdout.write(BOLD)
print("Enter the code of your preferred language: ", end="")
sys.stdout.write(RESET)
while language not in [lang["code"] for lang in lang_json]:
    language = input()

# Create super administrator
user_dict = dict(
    {"whatsapp:" + phone_number: {"lang": language, "role": "super"}})

# Create a key or Retrieve a key if file already exists
if not os.path.isfile("json/key.key"):
    key = Fernet.generate_key()
    with open("json/key.key", "xb") as file:
        file.write(key)
else:
    with open("json/key.key", "rb") as file:
        key = file.read()

# Create super administrator
user_list = json.dumps(user_dict, indent=4)
# Create byte version of JSON string
user_list_byte = user_list.encode("utf-8")
f = Fernet(key)
encrypted_data = f.encrypt(user_list_byte)
try:
    with open(f"bot_subscribers/{file_name}", "xb") as file:
        file.write(encrypted_data)
except FileExistsError:
    sys.stdout.write(BOLD + RED)
    print(
        f"\nA file under bot_subscribers/{file_name} already exists. " +
        "Delete and try again.")
    sys.stdout.write(RESET)
    sys.exit(1)
