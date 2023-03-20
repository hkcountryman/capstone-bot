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