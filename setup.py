"""Necessary JSON setup for Chatbot usage.

This is a basic Python script to be run to set-up the JSON file storing user
data to be used for all of the included Chatbot functionality.
"""

import json
import os
import sys
from typing import Dict, List

from cryptography.fernet import Fernet  # type: ignore [import]

# Term color codes
RED = "\033[1;31m"
GREEN = "\033[1;32m"
BOLD = "\033[;1m"
RESET = "\033[0;0m"

# File names
JSON_DIR = "json"
JSON_FILE = "subscribers.json"
BACKUP_FILE = "subscribers_bak.json"
KEY_FILE = "subscribers_key.key"
LOGS_FILE = "logs.json"
BACKUP_LOGS_FILE = "logs_bak.json"
LOGS_KEY_FILE = "logs_key.key"


print("Setting up user data file...\n")

# Get superuser phone number
sys.stdout.write(BOLD)
print(
    "Enter your WhatsApp phone number. Include country code prefaced by a '+'")
print("character and no other punctuation: ", end="")
sys.stdout.write(RESET)
phone_number = ""
# Checks for the '+' sign
while not phone_number.startswith("+"):
    phone_number = input()
    if not phone_number[1:].isdigit():
        phone_number = ""

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
sys.stdout.write(BOLD)
print("Enter the code of your preferred language: ", end="")
sys.stdout.write(RESET)
language = input()
while language not in [lang["code"] for lang in lang_json]:
    print("Invalid language; choose another: ", end="")
    language = input()

# Get superuser preferred display name
sys.stdout.write(BOLD)
print("\nEnter a display name (spaces will be removed): ", end="")
sys.stdout.write(RESET)
display_name = input().replace(" ", "")  # remove spaces
while display_name == "" or display_name.startswith("whatsapp:"):
    print("Invalid display name; choose another: ", end="")
    display_name = input().replace(" ", "")  # remove spaces

# Create subscriber dictionary with superuser
user_dict = dict({f"whatsapp:{phone_number}": {
                 "lang": language, "name": display_name, "role": "super"}})

# Look for json directory and create if needed
if not os.path.exists(f"{JSON_DIR}/"):
    os.makedirs(f"{JSON_DIR}/")

# Create a key or retrieve a key if file already exists for user data
if not os.path.isfile(f"{JSON_DIR}/{KEY_FILE}"):
    key = Fernet.generate_key()
    with open(f"{JSON_DIR}/{KEY_FILE}", "xb") as file:
        file.write(key)
else:
    with open(f"{JSON_DIR}/{KEY_FILE}", "rb") as file:
        key = file.read()

# Create super administrator
user_list = json.dumps(user_dict, indent=4)
# Create byte version of JSON string
user_list_byte = user_list.encode("utf-8")
f = Fernet(key)
encrypted_data = f.encrypt(user_list_byte)

print()

try:
    with open(f"{JSON_DIR}/{JSON_FILE}", "xb") as file:
        file.write(encrypted_data)
    sys.stdout.write(BOLD + GREEN)
    print(f"{JSON_DIR}/{JSON_FILE} created.")
    sys.stdout.write(RESET)
except FileExistsError:
    sys.stdout.write(BOLD + RED)
    print(
        f"A file under {JSON_DIR}/{JSON_FILE} already exists. " +
        "Delete and try again if you're certain.")
    sys.stdout.write(RESET)
    sys.exit(1)

try:
    with open(f"{JSON_DIR}/{BACKUP_FILE}", "xb") as file:
        file.write(encrypted_data)
    sys.stdout.write(BOLD + GREEN)
    print(f"{JSON_DIR}/{BACKUP_FILE} created.")
    sys.stdout.write(RESET)
except FileExistsError:
    sys.stdout.write(BOLD + RED)
    print(
        f"A file under bot_subscribers/{BACKUP_FILE} already exists. " +
        "Delete and try again if you're certain.")
    sys.stdout.write(RESET)
    sys.exit(1)

# Create a key or Retrieve a key if file already exists for logs data
if not os.path.isfile(f"{JSON_DIR}/{LOGS_KEY_FILE}"):
    key2 = Fernet.generate_key()
    with open(f"{JSON_DIR}/{LOGS_KEY_FILE}", "xb") as file:
        file.write(key2)
else:
    with open(f"{JSON_DIR}/{LOGS_KEY_FILE}", "rb") as file:
        key2 = file.read()

# Create logs file
# TODO: update to new format
logs_dict: Dict[str, Dict[str, List[str]]] = dict(
    {f"whatsapp:{phone_number}": {"timestamps": []}})
logs_list = json.dumps(logs_dict, indent=4)
# Create byte version of JSON string
logs_list_byte = logs_list.encode("utf-8")
f = Fernet(key2)
logs_encrypted_data = f.encrypt(logs_list_byte)

try:
    with open(f"{JSON_DIR}/{LOGS_FILE}", "xb") as file:
        file.write(logs_encrypted_data)
    sys.stdout.write(BOLD + GREEN)
    print(f"{JSON_DIR}/{LOGS_FILE} created.")
    sys.stdout.write(RESET)
except FileExistsError:
    sys.stdout.write(BOLD + RED)
    print(
        f"A file under {JSON_DIR}/{LOGS_FILE} already exists. " +
        "Delete and try again.")
    sys.stdout.write(RESET)
    sys.exit(1)

try:
    with open(f"{JSON_DIR}/{BACKUP_LOGS_FILE}", "xb") as file:
        file.write(logs_encrypted_data)
    sys.stdout.write(BOLD + GREEN)
    print(f"{JSON_DIR}/{BACKUP_LOGS_FILE} created.")
    sys.stdout.write(RESET)
except FileExistsError:
    sys.stdout.write(BOLD + RED)
    print(
        f"A file under {JSON_DIR}/{BACKUP_LOGS_FILE} already exists. " +
        "Delete and try again.")
    sys.stdout.write(RESET)
    sys.exit(1)
