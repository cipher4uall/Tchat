"""
Database management module for Tchat.

This module handles:
- SQLite database connection and initialization.
- Event logging.
- Session management.
- Encrypted message storage using day-partitioned tables.
"""
import sqlite3
import datetime
import os
import tchat_message

DB_NAME = "chat_history.db"

class ChatDatabase:
    """
    Manages the local SQLite database for chat history.
    """
    def __init__(self, db_path=DB_NAME):
        """
        Initializes the database connection.
        
        Args:
            db_path (str): Path to the SQLite database file.
        """
        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.init_global_tables()
            self.log_event("STARTUP", "Database initialized successfully.")
        except Exception as e:
            print(f"Failed to connect to database: {e}")

    def init_global_tables(self):
        """Creates the global tables (sessions, event_logs) if they don't exist."""
        if not self.conn:
            return

        cursor = self.conn.cursor()
        
        # Event Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                event_type TEXT,
                details TEXT
            )
        """)

        # Sessions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_name TEXT,
                server_ip TEXT,
                server_port INTEGER,
                start_time TEXT,
                end_time TEXT
            )
        """)
        
        self.conn.commit()

    def log_event(self, event_type, details):
        """
        Logs an event to the database.
        
        Args:
            event_type (str): Category of the event (e.g., 'CRASH', 'INFO').
            details (str): Description of the event.
        """
        if not self.conn:
            return
        
        try:
            timestamp = datetime.datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO event_logs (timestamp, event_type, details) VALUES (?, ?, ?)",
                           (timestamp, event_type, details))
            self.conn.commit()
        except Exception as e:
            print(f"Failed to log event: {e}")

    def get_daily_table_name(self, date_obj=None):
        """
        Returns the table name for a specific date.
        
        Args:
            date_obj (datetime.date): The date to generate the name for. Defaults to today.
        """
        if date_obj is None:
            date_obj = datetime.date.today()
        return f"messages_{date_obj.strftime('%Y%m%d')}"

    def ensure_daily_table(self, date_obj=None):
        """
        Creates the message table for the given date if it doesn't exist.
        
        Args:
            date_obj (datetime.date): The date for the table.
        """
        if not self.conn:
            return

        table_name = self.get_daily_table_name(date_obj)
        cursor = self.conn.cursor()
        
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                timestamp TEXT,
                sender TEXT,
                encrypted_content TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id)
            )
        """)
        self.conn.commit()
        return table_name

    def start_session(self, server_name, ip, port):
        """
        Records the start of a new chat session.
        
        Args:
            server_name (str): Name of the server.
            ip (str): IP address of the server.
            port (int): Port of the server.
            
        Returns:
            int: The new session ID.
        """
        if not self.conn:
            return -1

        try:
            timestamp = datetime.datetime.now().isoformat()
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (server_name, server_ip, server_port, start_time)
                VALUES (?, ?, ?, ?)
            """, (server_name, ip, port, timestamp))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            self.log_event("ERROR", f"Failed to start session: {e}")
            return -1

    def store_message(self, session_id, sender, message, key):
        """
        Encrypts and stores a message in the daily table.
        
        Args:
            session_id (int): The ID of the current session.
            sender (str): Name of the sender.
            message (str): The plaintext message content.
            key (bytes): The encryption key used for the session.
        """
        if not self.conn:
            return

        try:
            # Encrypt the message. If key is None, it remains plaintext (or handled by encrypt_content logic)
            # User requested encrypted storage. 
            # If the session has no key (public chat), we can generate a local key or just store as is.
            # However, the requirement is "secure data storage". 
            # If the user hasn't provided a key, we might need a default one or just store it.
            # Assuming we use the provided session key. If None, we interpret as "no encryption requested by user for this chat".
            # BUT, the user said "local SQLite file... should be encrypted". 
            # Ideally, we should encrypt everything with a user's local password, but we don't have a login system.
            # We will use the session encryption key for now, as implied by "encrypted using the same encryption key used for the chat session".
            
            encrypted_content = tchat_message.encrypt_content(message, key)
            
            timestamp = datetime.datetime.now().isoformat()
            table_name = self.ensure_daily_table()
            
            cursor = self.conn.cursor()
            cursor.execute(f"""
                INSERT INTO {table_name} (session_id, timestamp, sender, encrypted_content)
                VALUES (?, ?, ?, ?)
            """, (session_id, timestamp, sender, encrypted_content))
            self.conn.commit()
        except Exception as e:
            self.log_event("ERROR", f"Failed to store message: {e}")

    def get_recent_sessions(self, limit=10):
        """
        Retrieves a list of recent chat sessions.
        
        Returns:
            list: List of tuples (id, server_name, server_ip, start_time).
        """
        if not self.conn:
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"""
                SELECT id, server_name, server_ip, start_time 
                FROM sessions 
                ORDER BY start_time DESC 
                LIMIT {limit}
            """)
            return cursor.fetchall()
        except Exception as e:
            self.log_event("ERROR", f"Failed to fetch sessions: {e}")
            return []

    def load_session_history(self, session_id, key):
        """
        Loads and decrypts messages for a specific session.
        
        Args:
            session_id (int): ID of the session to restore.
            key (bytes): Encryption key for decryption.
            
        Returns:
            list: List of (sender, message) tuples.
        """
        if not self.conn:
            return []

        messages = []
        try:
            # We need to find which daily tables cover this session. 
            # A simple approach is to look at the session start time and assume it's mostly that day.
            # Or simpler: Query all tables. But that's expensive.
            # Given the constraint, let's query the sessions table to get the start time.
            cursor = self.conn.cursor()
            cursor.execute("SELECT start_time FROM sessions WHERE id = ?", (session_id,))
            result = cursor.fetchone()
            if not result:
                return []
            
            start_time_str = result[0]
            start_date = datetime.datetime.fromisoformat(start_time_str).date()
            
            # For now, let's assume session doesn't span multiple days, or check a range.
            # We will check the table for that start date.
            table_name = self.get_daily_table_name(start_date)
            
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                return []

            cursor.execute(f"""
                SELECT sender, encrypted_content 
                FROM {table_name} 
                WHERE session_id = ? 
                ORDER BY timestamp ASC
            """, (session_id,))
            
            rows = cursor.fetchall()
            for sender, encrypted_content in rows:
                decrypted_message = tchat_message.decrypt_content(encrypted_content, key)
                messages.append((sender, decrypted_message))
                
            return messages
        except Exception as e:
            self.log_event("ERROR", f"Failed to load history: {e}")
            return []
            
    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
