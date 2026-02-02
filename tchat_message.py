import pickle
import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

try:
    with open("chat.config", "r") as f:
        config_content = f.read()
        # Parse SALT = "value"
        for line in config_content.splitlines():
            if "SALT" in line:
                SALT_VALUE = line.split("=")[1].strip().strip('"').strip("'").rstrip(".")
                SALT = SALT_VALUE.encode()
                break
except:
    SALT = b'default_salt'

TEXT_COLOR_DEFAULT = 1
TEXT_COLOR_GREEN = 2
TEXT_COLOR_RED = 3
TEXT_COLOR_YELLOW = 4
TEXT_COLOR_BLUE = 5
CONSOLE_SUCCESS = "[+]"
CONSOLE_FAIL = "[-]"
CONSOLE_INFO = "[~]"
CONSOLE_SEPERATOR = " "
MESSAGE_GENERAL = 0
MESSAGE_INFO = 1


class InfoMessage():
    def __init__(self, server_name, max_clients, connected_clients, clients_info_dict, server_end):
        self.server_name = server_name
        self.message_type = MESSAGE_INFO
        self.max_clients = max_clients
        self.connected_clients = connected_clients
        self.clients_info_dict = clients_info_dict
        self.server_end = server_end


class GeneralMessage():
    def __init__(self, sender_name, separator, message, text_color):
        self.message_type = MESSAGE_GENERAL
        self.sender_name = sender_name
        self.separator = separator
        self.message = message
        self.text_color = text_color
        self.total_length = len(sender_name + separator + message) 


def general_message_encode(sender_name, separator, message, text_color):
    return pickle.dumps(GeneralMessage(sender_name, separator, message, text_color))

def info_message_encode(server_name, max_clients, connected_clients, clients_info_dict, server_end):
    return pickle.dumps(InfoMessage(server_name, max_clients, connected_clients, clients_info_dict, server_end))

def message_decode(message_object):
    return pickle.loads(message_object)

def derive_key(password):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def encrypt_content(plaintext, key):
    if key is None:
        return plaintext
    
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode('utf-8')

def decrypt_content(encrypted_text, key):
    if key is None:
        return encrypted_text
    
    try:
        data = base64.b64decode(encrypted_text)
        nonce = data[:12]
        ciphertext = data[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, None).decode('utf-8')
    except Exception as e:
        return "[Encrypted Message]"

