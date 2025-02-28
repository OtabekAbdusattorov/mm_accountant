import sqlite3

class TempTableManager:
    def __init__(self, db):
        self.db = db

    def user_exists(self, user_id):
        """Check if a user already has an entry in the temp table."""
        connection = sqlite3.connect(self.db)
        cursor = connection.cursor()
        cursor.execute("SELECT user_id FROM temp_requests WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone() is not None
        connection.close()
        return exists

    def insert_user(self, user_id):
        """Insert a new user entry if they don't exist."""
        if not self.user_exists(user_id):
            connection = sqlite3.connect(self.db)
            with connection:
                connection.execute("INSERT INTO temp_requests (user_id) VALUES (?)", (user_id,))
            connection.close()

    def update_temp_results(self, user_id, column, value):
        connection = sqlite3.connect(self.db)
        with connection:
            connection.execute(
                f"UPDATE temp_requests SET {column} = ? WHERE user_id = ?", (value, user_id)
            )

    def get_temp_results(self, user_id):
        connection = sqlite3.connect(self.db)
        cursor = connection.cursor()
        cursor.execute(
            "SELECT model, vin, plate_number, last_price, vat_value, phoneNumber FROM temp_requests WHERE user_id = ?",
            (user_id,)
        )
        result = cursor.fetchone()
        connection.close()
        return result

    def clear_temp_request(self, user_id):
        connection = sqlite3.connect(self.db)
        with connection:
            connection.execute("DELETE FROM temp_requests WHERE user_id = ?", (user_id,))
        connection.close()

    ### related to vin column and requests table
    def vin_exists(self, vin):
        """Check if a VIN already exists in the requests table."""
        connection = sqlite3.connect(self.db)
        cursor = connection.cursor()

        cursor.execute("SELECT vin FROM requests WHERE vin = ?", (vin,))
        result = cursor.fetchone()

        connection.close()
        return result is not None