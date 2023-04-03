"""Necessary JSON setup for Chatbot usage.

This module contains a basic Python script to be run to set-up the JSON file
storing user data to be used for all of the included Chatbot functionality.
"""

import json
from cryptography.fernet import Fernet
import os

print("Setting up user data file...")

# Get administrator user data
phone_number = input("Enter your WhatsApp number: ")
language = input("Enter your preferred language: ")

# Create super administrator
user_dict = dict(
    {'whatsapp:+1' + phone_number: {'lang': language, 'role': 'super'}})

# Create a key or Retrieve a key if file already exists
if not os.path.isfile("json/key.key"):
    key = Fernet.generate_key()
    with open("json/key.key", 'xb') as file:
        file.write(key)
else:
    with open("json/key.key", 'rb') as file:
        key = file.read()

# Create super administrator
user_list = json.dumps(user_dict, indent=4)
# Create byte version of JSON string
user_list_byte = user_list.encode('utf-8')
f = Fernet(key)
encrypted_data = f.encrypt(user_list_byte)
with open("bot_subscribers/team56test.json", 'xb') as file:
    file.write(encrypted_data)
with open("bot_subscribers/backup.json", 'xb') as file:
    file.write(encrypted_data)
