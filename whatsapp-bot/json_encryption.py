#Option 1
from cryptography.fernet import Fernet

# 128-bit AES cipher key
# Must be stored in an accessible, read-only manner
key = Fernet.generate_key()
with open('key.key', 'wb') as file:
	file.write(key)

# Retrieve key
with open('key.key', 'rb') as file:
	key = file.read()

# Retrieve JSON file
with open('example.json', 'rb') as file:
	json_data = file.read()

# Encryption
fernet = Fernet(key)
encrypted_data = fernet.encrypt(data)

# Decryption
fernet = Fernet(key)
decrypted_data = fernet.decrypt(data)


#Option 2
import json
import objcrypt

# 'Any key can be used in place of 'abc'
crypter = objcrypt.Crypter('key', 'abc')
python_dictionary = {
	'name': 'kevin'
}
# Encrypt Python object
encrypted_data = crypter.encrypt_object(python_dictionary)

# Encrypt JSON
json_dictionary = json.loads(python_dictionary)
encrypted_json = crypter.encrypt_json(json_dictionary)

# Decryption
decrypted_data = crypter.decrypt_object(encrypted_data)
decrypted_json = crypter.decrypt_json(encrypted_json)