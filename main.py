"""
Main entry point for the Tchat application.

This module handles the initialization of the application, including:
- Argument parsing for server and client commands.
- Managing the main event loop for the GUI.
- coordinating between the GUI, server, and client components.
"""
import threading

import curses
from curses import wrapper
import argparse

import tchat_gui
import tchat_server
import tchat_client
import tchat_message


class ArgumentParser(argparse.ArgumentParser):    
    def _get_action_from_name(self, name):
        """Given a name, get the Action instance registered with this parser.
        
        Args:
            name (str): The name of the action to find.
            
        Returns:
            argparse.Action: The action object if found, otherwise None.
        """
        container = self._actions
        if name is None:
            return None
        for action in container:
            if '/'.join(action.option_strings) == name:
                return action
            elif action.metavar == name:
                return action
            elif action.dest == name:
                return action

    def error(self, message):
        raise message

class Main():
    """
    Main application controller.
    
    This class manages the lifecycle of the application, handling user input,
    gui updates, and the state of client/server threads.
    """
    def __init__(self):
        """Initialize the Main application, setting up state and parser."""
        self.setup_parser()
        self.running_gui = False
        self.running_server = False
        self.running_client = False
        self.username = "You"
        self.username = "You"
        self.seperator = ": "
        self.key = None
    
    def setup_parser(self):
        """Configures the argument parser for handling commands like /server and /join."""
        self.top_parser = ArgumentParser(description="Command line parser", add_help=False, exit_on_error=False)

        subparsers = self.top_parser.add_subparsers(dest='command', help="Available commands")

        server_parser = subparsers.add_parser('/server', help="Start a server")
        server_parser.add_argument('-p', '--port', type=int, help="Port number", default=5050)
        server_parser.add_argument('-i', '--ip', help="IP address", default="localhost")
        server_parser.add_argument('-n', '--name', help="Server name", default="MyServer")
        server_parser.add_argument('-k', '--key', help="Encryption key (password)", default=None)

        connect_parser = subparsers.add_parser('/join', help="Connect to a server")
        connect_parser.add_argument('-p', '--port', type=int, help="Port number", default=5050)
        connect_parser.add_argument('-i', '--ip', help="IP address", default="localhost")
        connect_parser.add_argument('-k', '--key', help="Encryption key (password)", default=None)


    def run_gui(self, stdscr):
        """
        Main loop for the Curses GUI.
        
        Args:
            stdscr: The curses standard screen object.
        """
        self.gui = tchat_gui.Gui(stdscr)
        self.gui.win_draw_global()
        self.running_gui = True

        while self.running_gui:
            user_input = stdscr.getch()
            if self.gui.pager_mode:
                self.gui.handle_pager_input(user_input)
                continue
                
            if user_input == curses.KEY_RESIZE:
                self.gui.handle_resize()
            elif 32 <= user_input <= 126:
                self.gui.handle_character_input(user_input)
            elif user_input == curses.KEY_LEFT:
                self.gui.handle_left()
            elif user_input == curses.KEY_RIGHT:
                self.gui.handle_right()
            elif user_input == curses.KEY_UP and not self.gui.shows_first_message:
                self.gui.chat_scroll_index += 1
                self.gui.win_draw_semi()
            elif user_input == curses.KEY_DOWN:
                if self.gui.chat_scroll_index > 0:
                    self.gui.chat_scroll_index -= 1
                    self.gui.win_draw_semi()
            elif user_input == curses.KEY_ENTER or user_input ==  10 or user_input == 13:
                user_message = self.gui.get_user_input().strip()
                self.gui.handle_enter()
                if user_message.startswith("/"):
                    self.user_command(user_message)
                elif user_message.strip() == "":
                    pass
                else:
                    final_message = user_message
                    if self.key:
                        final_message = tchat_message.encrypt_content(user_message, self.key)

                    if self.running_server:
                        message_object = tchat_message.general_message_encode("[SERVER]", " ", final_message, tchat_message.TEXT_COLOR_BLUE)
                        self.server.message_broadcast(message_object)
                    elif self.running_client:
                        message_object = tchat_message.general_message_encode("_", "_", final_message, tchat_message.TEXT_COLOR_DEFAULT)
                        self.client.send_message(message_object)
                    else:
                        self.gui.new_message(self.username, self.seperator, user_message)
                
            elif user_input == curses.KEY_BACKSPACE or user_input == 127 or user_input == 8:
                self.gui.handle_backspace()
            elif user_input == curses.KEY_DC:
                self.gui.handle_delete()

    def user_command(self, whole_command):
        """
        Parses and executes user commands entered in the chat.
        
        Args:
            whole_command (str): The full command string including arguments.
        """
        whole_command = list(whole_command.strip().split(" "))
        command = whole_command[0]

        try:
            if command == "/quit":
                self.quit()
            elif command == "/server":
                if self.running_client:
                    self.gui.console_message_fail(f"You are already running a client...")
                elif self.running_server:
                    self.gui.console_message_fail(f"You are already running a server...")     
                else:
                    self.start_server(whole_command)

            elif command == "/join":
                if self.running_client:
                    self.gui.console_message_fail(f"You are already running a client...")
                elif self.running_server:
                    self.gui.console_message_fail(f"You are already running a server...")
                else:
                    self.start_client(whole_command)

            elif command =="/disconnect" or command == "/disc":
                if self.running_client:
                    self.quit_client()
                elif self.running_server:
                    self.quit_server()
                else:
                    self.gui.console_message_fail(f"No server or client is running...")
            elif command == "/bottom" or command == "/b":
                self.gui.chat_scroll_index = 0
                self.gui.win_draw_semi()
            elif command == "/clear":
                if self.running_server:
                    self.gui.console_message_fail(f"Server can't clear chatbox, because uhh.. reasons.")
                else:
                    self.gui.chatbox_messages.clear()
                    self.gui.win_draw_semi()
            elif command == "/help":
                try:
                    with open("help.md", "r") as f:
                        text = f.read()
                        self.gui.enable_pager(text)
                except Exception as e:
                    self.gui.console_message_fail(f"Could not load help.md: {e}")
            else:
                self.gui.console_message_fail("Unknown command...")


        except Exception as e:
            self.gui.console_message_fail(f"Error: {e}")

    def quit_client(self):
        """Stops the client thread and cleans up resources."""
        self.client.stop_client()
        self.running_client = False
        self.process_client.join()
        self.gui.sidebar_data = None
        self.gui.win_draw_sidebar()

    def quit_server(self):
        """Stops the server thread and cleans up resources."""
        self.server.stop_server()
        self.running_server = False
        self.process_server.join()
        self.gui.sidebar_data = None
        self.gui.win_draw_sidebar()

    def quit(self):
        """Exits the application, ensuring client/server threads are stopped."""
        if self.running_server:
            self.quit_server()
        elif self.running_client:
            self.quit_client()

        self.running_gui = False
        self.process_gui.join()

    def start_gui(self):
        """Starts the GUI in a separate thread."""
        self.process_gui = threading.Thread(target=wrapper(self.run_gui))
        self.process_gui.start()

    def start_server(self, whole_command):
        """
        Starts the chat server based on provided arguments.
        
        Args:
            whole_command (list): List of command line arguments for the server.
        """
        args = None
        try:
            args = self.top_parser.parse_args(whole_command)
        except Exception as e:
            self.gui.console_message_fail(e)
            return
        if tchat_server.is_port_available(args.port):
            
            if args.key:
                self.key = tchat_message.derive_key(args.key)
                self.gui.console_message_info(f"Encryption enabled with key.")

            self.server = tchat_server.Server(self.gui, args.ip, args.port, args.name, key=self.key)
            self.process_server = threading.Thread(target=self.server.run_server)
            self.running_server = True
            self.process_server.start()
        else:
            self.gui.console_message_fail(f"Port is reserved or unavailable...")

    def start_client(self, whole_command):
        """
        Starts the chat client and connects to a server.
        
        Args:
            whole_command (list): List of command line arguments for the client.
        """
        args = None
        try :
            args = self.top_parser.parse_args(whole_command)
        except Exception as e:
            self.gui.console_message_fail(f"{e}")
            return



        if args.key:
            self.key = tchat_message.derive_key(args.key)
            self.gui.console_message_info(f"Encryption enabled with key.")

        self.client = tchat_client.Client(self.gui, args.ip, args.port, key=self.key)
        try:
            self.client.start_connection()
        except:
            self.gui.new_message(tchat_message.CONSOLE_FAIL, tchat_message.CONSOLE_SEPERATOR, f"Unable to connect to server with {args.ip}:{args.port}", tchat_message.TEXT_COLOR_RED)
            return
        self.process_client = threading.Thread(target=self.client.run_client)
        self.running_client = True
        self.process_client.start()

if __name__ == "__main__":
    main = Main()
    main.start_gui()