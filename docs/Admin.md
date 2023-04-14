# Administrator Commands

## Adding a new user

```
/add [WhatsApp number] [Language code] [Display name] [User type]
```

Required Fields:

- WhatsApp number - User's WhatsApp number (__Must__ include '+' and country code)
- Language code - User's preferred language code. More information can be found in the Languages.md file.
- Display name - User's display name (__No spaces allowed__)
- User type - Super administrator (super), administrator (admin), or regular user (user)

Error(s):

- Incorrect number of arguments delimited by space(s)
- Invalid language code
- Invalid user type
- WhatsApp number already exists in the group chat


## Removing a user

```
/remove [WhatsApp number]
```

Required Fields:

- WhatsApp number - User's WhatsApp number (__Must__ include '+' and country code)

**OR**

```
/remove [Display name]
```

Required Fields:

- Display name - User's display name (__No spaces allowed__)

Error(s):

- Incorrect number of arguments delimited by space(s)
- WhatsApp number does not exist in the group chat

**Note:** An administrator cannot remove himself/herself. An administrator also cannot remove a super administrator.

## List all users

A list of users in the group chat will be displayed in a readable format.

```
/list
```

## Test translate

Return a message that has first been translated to the target language and then back to the user's native language.

```
/test [Language code] [Test message]
```

Required Fields:

- Language code - Target language code. More information can be found in the Languages.md file.
- Test message - Test message

## Generate statistics

### Number of messages by a specific user within a given time frame

A text message containing the specific user's number of messages will be displayed.

```
/stats [Time length] day[s] [WhatsApp number]
```

Required Fields:

- Time length - Number of days
- WhatsApp number - User's WhatsApp number (**Must** include '+' and country code)

**OR**

```
/stats [Time length] days [Display Name]
```

Required Fields:

- Time length - Number of days
- Display name - User's display name (**No spaces allowed**)

### Number of messages by all users within a given time frame

A text message containing all users' corresponding number of messages will be displayed in a readable format.

```
/stats [Time length] days
```

Required Fields:

- Time length - Number of days

### Timestamp of the last message by a specific user

A text message containing the specific user's most recent message timestamp will be displayed.

```
/lastpost [WhatsApp number]
```

Required Fields:

- WhatsApp number - User's WhatsApp number (**Must** include '+' and country code)

**OR**

```
/lastpost [Display Name]
```

Required Fields:

- Display name - User's display name (**No spaces allowed**)

### Timestamp of the last message by all users

A text message containing all users' corresponding most recent message timestamp will be displayed in a readable format.

```
/lastpost
```

## Changing User Language, User Type and More

Please utilize the `/remove` and `/add` commands, in order, to update a user's settings. 
