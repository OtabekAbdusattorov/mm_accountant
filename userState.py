import sqlite3
from datetime import datetime

class UserStateManager:
    def __init__(self, db):
        self.db = db
        self.user_states = {}

    def connect(self):
        """Create a connection to the database."""
        return sqlite3.connect(self.db)

    def get_state(self, user_id):
        """Retrieve the latest state of a user."""
        state = ''
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT state FROM userStates 
                WHERE user_id = ? 
                ORDER BY id DESC 
                LIMIT 1
            """, (user_id,))
            result = cursor.fetchone()
            if result:
                state = result[0]
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
        finally:
            connection.close()
        return state

    def insert_state(self, user_id, user_state):
        """Insert a new user state into the database."""
        connection = self.connect()
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with connection:
            connection.execute("""
                INSERT INTO userStates (user_id, state, date) 
                VALUES (?, ?, ?)
            """, (user_id, user_state, now_time))
        connection.close()

    def update_state(self, user_id, user_state):
        """Update an existing user state in the database."""
        connection = self.connect()
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with connection:
            connection.execute("""
                UPDATE userStates 
                SET state = ?, date = ? 
                WHERE user_id = ?
            """, (user_state, now_time, user_id))

    def user_state(self, message, new_state):
        """Update or insert a user state based on their last known state."""
        user_id = message.chat.id
        self.user_states[message.chat.id] = new_state

        current_state = self.get_state(user_id)
        if not current_state:
            self.insert_state(user_id, new_state)
        else:
            self.update_state(user_id, new_state)