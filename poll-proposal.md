# Polling idea

## Syntax

```
/poll [timestamp]
What do you pick?
Option A
Option B
```

Users would then receive a message like

```
New poll due at [timestamp]!
What do you pick?
1. Option A
2. Option B
Reply to this message with the number you want. You may vote again to change your vote.
```

They right-swipe on the message and send in a number, which can be validated, and all the votes get tallied. The timestamp format can be whatever we want.

## New class: `Poll`

Objects of this type are instantiated in a `Chatbot` instance, probably just in a list. Once a poll is finished, remove it from the list (be sure to account for possible exceptions, see this reference: https://datagy.io/python-list-pop-remove-del-clear/).

### Members:

- `uid`: unique ID (totally internal, shouldn't be visible in the poll message or used by users voting in the poll)
- `question`: thing to vote on
- `timer`: time when poll closes (see this code for how to asynchronously deal with a timer: https://stackoverflow.com/a/45430833)
- `num_votes`: dictionary of options correlating options with number of votes
- `options`: list of options, indexed numerically so that users can reply to a poll with a number and it is translated to an option, which can then be looked up in num_votes
- `user_votes`: dictionary of each user and their vote

### Methods:

- `_init_(question, time, num_votes, user_votes, uid=None)`: constructor (leave out `uid` a new poll but not for a restored poll from the JSON file)
- `vote(option_number, user_contact)`: for the selected option, add a vote and put the user contact down for voting for that (may need to subtract a vote from somewhere if they're already down as voted)
- `get_results()`: at the appointed time, push out the results to everyone (may need to modify `_push()` as I don't think it's currently suitable, or we could make another function)

### Issue

We need some way to send out the results on time. We could do this by starting a new thread for each `Poll` object on instantiation that just counts down the time. It may be more efficient not to do that, though, and just use `at` or Cron to deal with it, letting a separate program run in the background and use its own JSON file and whatnot. See below.

## JSON representation of polls

In order to persist polls after the server shuts down, they will need to be stored as JSON. Currently, we have something like

```json
{
    "whatsapp:+12005555555": {
        "lang": "en",
        "role": "super"
    }
}
```

I propose we change it to something like this:

```json
{
    "contacts": {
        "whatsapp:+12005555555": {
            "lang": "en",
            "role": "super"
        }
    },
    "polls": {
        "<uid>": {
            "question": "...?",
            "num_votes": {
                "option1": 0,
                "option2": 1
            },
            "user_votes": {
                "whatsapp:+12005555555": "option2"
            }
        }
    }
}
```

It's a little complicated but that's the simplest thing I can think of that allows people to vote again to change their vote. I'd probably go with this option.

By the way, using the same JSON file is easiest because it means keeping track of one file per chatbot (or per group chat) instead of two, but it might be overall harder. Kevin will be able to tell how much it inconveniences his stuff.
