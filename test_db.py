import tchat_database
import tchat_message
import os
import datetime

DB_FILE = "test_chat.db"

def test_database():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    
    print("Initializing DB...")
    db = tchat_database.ChatDatabase(DB_FILE)
    
    print("Testing Session 1 (Plaintext)...")
    s1 = db.start_session("PlainServer", "127.0.0.1", 5050)
    db.store_message(s1, "User1", "Hello World", None)
    
    msgs = db.load_session_history(s1, None)
    assert len(msgs) == 1
    assert msgs[0][1] == "Hello World"
    print("Session 1 Passed")
    
    print("Testing Session 2 (Encrypted)...")
    s2 = db.start_session("SecureServer", "127.0.0.1", 5051)
    key = tchat_message.derive_key("password")
    db.store_message(s2, "User1", "Secret Message", key)
    
    msgs = db.load_session_history(s2, key)
    assert len(msgs) == 1
    assert msgs[0][1] == "Secret Message"
    print("Session 2 Passed")
    
    print("Testing Daily Table...")
    table_name = db.get_daily_table_name()
    expected_name = f"messages_{datetime.date.today().strftime('%Y%m%d')}"
    assert table_name == expected_name
    
    db.close()
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    
    print("All tests passed!")

if __name__ == "__main__":
    test_database()
