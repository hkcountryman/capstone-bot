# TransLingo
![TransLing_logo](images/chatbot_logo.png)

## About

This WhatsApp bot holds one-on-one conversations with each subscriber in a "group chat". Members can be added by their WhatsApp number and have roles (user, admin, or superuser) as well as preferred languages. When a user messages the bot, the message is forwarded to all other members of the group, translated into their preferred language.

## Limitations

- Short messages may not be translated. The message language is autodetected, so the translation API requires enough text to determine the original language.
- WhatsApp polls, replies, and emoji reacts are not supported.
- If you choose to use a public translation server, you may face fairly long translation times. You will also negate the benefits of WhatsApp's end-to-end encryption.

## Getting started

See the wiki for [setup instructions for developers](https://github.com/hkcountryman/capstone-bot/wiki/Setup-instructions-for-developers) or [setup instructions for a production server](https://github.com/hkcountryman/capstone-bot/wiki/Setup-instructions-for-a-production-server).

Send messages you wish to send to the group to the bot as you normally would. For more information on special commands for the bot, see [the wiki page on bot commands](https://github.com/hkcountryman/capstone-bot/wiki/Bot-commands).
