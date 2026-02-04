"""
Server module for the Tchat application.

This module handles:
- Server socket creation and management.
- Client connections and disconnections.
- Message broadcasting and routing.
"""
import socket

import select
from datetime import datetime

import tchat_message

INTERVAL = 0.4
DATA_SIZE = 1024

def get_date():
    """Returns the current date in 'DD Mon 'YY' format."""
    datetime.now().strftime("%d %b '\'%y")

def get_time():
    """Returns the current time in 'HH:MM' format."""
    datetime.now().strftime("%H:%M")

def get_ip():
    """Returns the IP address of the current machine."""
    return socket.gethostbyname(socket.gethostname())

class ClientsInfo():
    """Stores information about a connected client."""
    def __init__(self, user_id, username, joined_date, joined_time):
        self.user_id = user_id
        if username:
            self.username = username
        else:
            self.username = user_id
        self.joined_date = joined_date
        self.joined_time = joined_time


class Server():
    """
    Tchat Server class.
    
    Manages the server socket, client connections, and message broadcasting.
    """
    def __init__(self, gui, ip, port, server_name, max_clients=12, key=None):
        """Initializes the server with the given parameters."""
        self.gui = gui
        self.ip_address = ip
        self.server_name = server_name
        self.port = port
        self.max_clients = max_clients
        self.key = key
        self.username = "[SERVER]"
        self.separator = " "
        self.connected_sockets = []
        self.sockets_names = {}
        self.new_client_id = 1
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip_address, self.port))
        self.server_socket.listen(max_clients)
        self.connected_sockets.append(self.server_socket)
        self.sockets_names[self.server_socket] = ClientsInfo("Server Instance", self.username, get_date(), get_time())
        self.is_running = False

    def create_update_message(self):
        """Creates a message containing current server status and connected clients."""
        return tchat_message.info_message_encode(self.server_name, self.max_clients, len(self.connected_sockets) - 1, list(self.sockets_names.values()), False)

    def run_server(self):
        """Main server loop handling new connections and incoming messages."""
        self.is_running = True
        self.gui.console_message_success(f"Server is starting on {self.ip_address}:{self.port} with the name: {self.server_name}")
        self.message_broadcast(self.create_update_message(), tchat_message.MESSAGE_INFO)
        while self.is_running:
            readable, _, _ = select.select(self.connected_sockets, [], [], INTERVAL)
            for connected_socket in readable:
                if connected_socket == self.server_socket:
                    client_socket, client_address = connected_socket.accept()
                    self.new_client(client_socket, client_address)
                    self.message_broadcast(self.create_update_message(), tchat_message.MESSAGE_INFO)
                else:
                    data = connected_socket.recv(DATA_SIZE)
                    if data:
                        # Yes, this is unintuitive
                        decoded_message = tchat_message.message_decode(data)
                        
                        sender_name = self.sockets_names[connected_socket].username
                        update_data = tchat_message.general_message_encode(sender_name, ": ", decoded_message.message, decoded_message.text_color)
                        self.message_broadcast(update_data)

                    else:
                        self.remove_client(connected_socket)
                        self.message_broadcast(self.create_update_message(), tchat_message.MESSAGE_INFO)

    def stop_server(self):
        """Stops the server and notifies clients."""
        msg_text = "Server has been closed, for clients use /disc to disconnect..."
        if self.key:
            msg_text = tchat_message.encrypt_content(msg_text, self.key)
        object = tchat_message.general_message_encode(tchat_message.CONSOLE_INFO, tchat_message.CONSOLE_SEPERATOR, msg_text, tchat_message.TEXT_COLOR_YELLOW)
        self.message_broadcast(object)
        self.is_running = False

    def new_client(self, socket, address):
        """
        Handles a new client connection.
        
        Args:
            socket: The client's socket object.
            address: The client's address tuple (IP, port).
        """
        name = "User#" + str(self.new_client_id)
        self.sockets_names[socket] = ClientsInfo(name, None, get_date(), get_time())
        self.new_client_id += 1
        self.connected_sockets.append(socket)
        
        msg_text = f"{name} has joined the server..."
        if self.key:
            msg_text = tchat_message.encrypt_content(msg_text, self.key)

        object = tchat_message.general_message_encode(tchat_message.CONSOLE_INFO, tchat_message.CONSOLE_SEPERATOR, msg_text, tchat_message.TEXT_COLOR_YELLOW)
        self.message_broadcast(object)


    def remove_client(self, client):
        """
        Removes a client from the server and notifies others.
        
        Args:
            client: The client socket to remove.
        """
        client.close()
        name = self.sockets_names[client].username
        del self.sockets_names[client]
        self.connected_sockets.remove(client)
        
        msg_text = f"{name} has left the server..."
        if self.key:
            msg_text = tchat_message.encrypt_content(msg_text, self.key)
            
        object = tchat_message.general_message_encode(tchat_message.CONSOLE_INFO, tchat_message.CONSOLE_SEPERATOR, msg_text, tchat_message.TEXT_COLOR_YELLOW)
        self.message_broadcast(object)

    def message_broadcast(self, message_object, type=tchat_message.MESSAGE_GENERAL):
        """
        Broadcasts a message to all connected clients.
        
        Args:
            message_object: The encoded message to send.
            type (int): The type of message (general or info).
        """
        for client in self.connected_sockets:
            if client != self.server_socket:
                try: 
                    client.send(message_object)
                except Exception as e:
                    print(e)
                    client.close()
                    self.remove_client(client)
        if type == tchat_message.MESSAGE_INFO:
            self.gui.win_draw_sidebar(message_object)
        elif type == tchat_message.MESSAGE_GENERAL:
            message = tchat_message.message_decode(message_object)
            
            display_text = message.message
            if self.key:
                display_text = tchat_message.decrypt_content(message.message, self.key)
            
            self.gui.new_message(message.sender_name, message.separator, display_text, message.text_color)

def is_port_available(port):
    """
    Checks if a given port is available for binding.
    
    Args:
        port (int): The port number to check.
        
    Returns:
        bool: True if the port is available, False otherwise.
    """
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.bind((host_ip, port))
        return True
    
    except:
        return False