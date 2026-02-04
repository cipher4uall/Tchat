"""
Client module for the Tchat application.

This module handles:
- Establishing a connection to the server.
- Sending and receiving messages.
- Processing incoming messages and updating the GUI.
"""
import socket

import select
import tchat_message

INTERVAL = 0.4
DATA_SIZE = 1024
CONNECTION_TIMEOUT = 4

class Client():
    """
    Tchat Client class.
    
    Manages the client-side network operations, including connecting to the server
    and handling the message loop.
    """
    def __init__(self, gui, server_ip, server_port, key=None, db=None, session_id=None):
        """Initializes the client with connection details."""
        self.gui = gui
        self.server_ip = server_ip
        self.server_port = server_port
        self.key = key
        self.db = db
        self.session_id = session_id

        self.is_running = False

    def start_connection(self):
        """Establishes a socket connection to the server."""
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(CONNECTION_TIMEOUT)
        self.client_socket.connect((self.server_ip, self.server_port))

    def run_client(self):
        """Main loop that listens for incoming messages from the server."""
        self.is_running = True

        while self.is_running:
            readable, _, _ = select.select([self.client_socket,], [], [], INTERVAL)
            for node in readable:
                try:
                    data = node.recv(DATA_SIZE)
                    if data:
                        
                        object = tchat_message.message_decode(data)

                        if object.message_type == tchat_message.MESSAGE_INFO:
                            self.gui.win_draw_sidebar(data)
                        else:
                            display_text = object.message
                            # Store raw message (encrypted or not)
                            if self.db and self.session_id:
                                # We store the message content. If we have a key, it should be encrypted.
                                # The object.message is plaintext if not encrypted, or ciphertext if encrypted?
                                # Wait, tchat_message logic:
                                # main.py calls encrypt_content BEFORE creating message object.
                                # So object.message is ALREADY encrypted if encryption is on.
                                # But decrypt_content is called below. 
                                # Let's check main.py: 
                                # final_message = tchat_message.encrypt_content(user_message, self.key)
                                # message_object = tchat_message.general_message_encode(..., final_message, ...)
                                # So object.message IS ciphertext (Base64 string).
                                
                                # Our DB expects plaintext and encrypts it itself if key is provided.
                                # Or we can just store what we have.
                                # If we pass the key to store_message, it will encrypt it AGAIN.
                                # If object.message is already encrypted, we should probably store it as is, or decrypt it then store it (so DB can re-encrypt it uniformly).
                                # User requirement: "message content must be encrypted using the same encryption key used for the chat session".
                                # If we receive encrypted content, and we store it directly, it is encrypted.
                                # But 'store_message' in db executes 'encryption_content(message, key)'.
                                # Double encryption?
                                
                                # Best approach: Decrypt it for display, then let DB encrypt it for storage.
                                # Or: Pass raw content and key=None to DB?
                                # Check decrypt logic below:
                                
                                pass

                            if self.key:
                                display_text = tchat_message.decrypt_content(object.message, self.key)
                            
                            # Now display_text is the plaintext.
                            if self.db and self.session_id:
                                # Store the plaintext version, let DB encrypt it.
                                self.db.store_message(self.session_id, object.sender_name, display_text, self.key)

                            self.gui.new_message(object.sender_name, object.separator, display_text, object.text_color)

                except Exception as e:
                    pass

    def send_message(self, message_object):
        """
        Sends a message to the server.
        
        Args:
            message_object: The encoded message object to send.
        """
        try:
            self.client_socket.send(message_object)
        except:
            self.gui.new_message(tchat_message.CONSOLE_FAIL, tchat_message.CONSOLE_SEPERATOR, "Error sending message, maybe the server is down...", tchat_message.TEXT_COLOR_RED)
    def stop_client(self):
        """Closes the connection and stops the client loop."""
        self.is_running = False
        self.client_socket.close()
        self.gui.new_message(tchat_message.CONSOLE_INFO, tchat_message.CONSOLE_SEPERATOR, "You disconnected from the server...", tchat_message.TEXT_COLOR_YELLOW)



