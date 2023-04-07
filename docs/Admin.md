## Administrator Commands

### Adding a New User
```
/add [WhatsApp number] [Language code] [Display name] [User type]
```
Required Fields:
- WhatsApp number - User's WhatsApp number (__Must__ include '+' and country code)
- Language code - User's preferred language code. More information can be found in the Languages.md file.
- Display name - User's display name (__No spaces allowed__)
- User type - Super administrator (super), administrator (admin), or regular user (user)

<br>Error(s):
- Incorrect number of arguments delimited by space(s)
- Invalid language code
- Invalid user type
- WhatsApp number already exists in the group chat


### Removing a User
```
/remove [WhatsApp number]
```
Required Fields:
- WhatsApp number - User's WhatsApp number (__Must__ include '+' and country code)

<br>Error(s):
- Incorrect number of arguments delimited by space(s)
- WhatsApp number does not exist in the group chat

<br>__Note:__ An administrator cannot remove himself/herself. An administrator also cannot remove a super administrator.


### List all Users
```
/list
```
A list of users in the group chat will be displayed in JSON format.


### Test Command
Return a message that has first been translated to the target language and then back to the user's native language.
```
/test [Language code] [Test message]
```
Required Fields:
- Language code - Target language code. More information can be found in the Languages.md file.
- Test message - Test message


### Generate Statistics
Option 1:
```
/stats [WhatsApp number] [Time length]
```
Required Fields:
- WhatsApp number - User's WhatsApp number (__Must__ include '+' and country code)
- Time length - 

<br>Option 2:

#### Changing User Language, User Type and More
Please utilize the `/remove` and `/add` commands, in order, to update a user's settings. 
