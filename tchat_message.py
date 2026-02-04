"""
Message handling module for Tchat.

This module provides:
- Message classes for different types of communication (General, Info).
- Serialization and deserialization using pickle.
- Encryption and decryption utilities using AES-GCM.
"""
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
    """
    Represents a system information message.
    
    Used for server updates like client counts and user lists.
    """
    def __init__(self, server_name, max_clients, connected_clients, clients_info_dict, server_end):
        """Initializes an InfoMessage with server statistics."""
        self.server_name = server_name
        self.message_type = MESSAGE_INFO
        self.max_clients = max_clients
        self.connected_clients = connected_clients
        self.clients_info_dict = clients_info_dict
        self.server_end = server_end


class GeneralMessage():
    """
    Represents a standard chat message.
    
    Used for user messages, private messages, and console notifications.
    """
    def __init__(self, sender_name, separator, message, text_color):
        """Initializes a GeneralMessage."""
        self.message_type = MESSAGE_GENERAL
        self.sender_name = sender_name
        self.separator = separator
        self.message = message
        self.text_color = text_color
        self.total_length = len(sender_name + separator + message) 


def general_message_encode(sender_name, separator, message, text_color):
    """Encodes a GeneralMessage into bytes."""
    return pickle.dumps(GeneralMessage(sender_name, separator, message, text_color))

def info_message_encode(server_name, max_clients, connected_clients, clients_info_dict, server_end):
    """Encodes an InfoMessage into bytes."""
    return pickle.dumps(InfoMessage(server_name, max_clients, connected_clients, clients_info_dict, server_end))

def message_decode(message_object):
    """Decodes bytes back into a Message object."""
    return pickle.loads(message_object)

def derive_key(password):
    """Derives a 32-byte key from a password using PBKDF2HMAC with a salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def encrypt_content(plaintext, key):
    """
    Encrypts plaintext using AES-GCM.
    
    Args:
        plaintext (str): The text to encrypt.
        key (bytes): The encryption key.
        
    Returns:
        str: Base64 encoded string containing nonce + ciphertext.
    """
    if key is None:
        return plaintext
    
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode('utf-8')

def decrypt_content(encrypted_text, key):
    """
    Decrypts encrypted text using AES-GCM.
    
    Args:
        encrypted_text (str): Base64 encoded string containing nonce + ciphertext.
        key (bytes): The decryption key.
        
    Returns:
        str: Decrypted plaintext or an error message if decryption fails.
    """
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

