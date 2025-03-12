import sqlite3

db = 'account'


def insert_admin(admin_id, request_id, status_req, payment_status, message_id, date):
    connection = sqlite3.connect(db)
    with connection:
        connection.execute(
            "INSERT INTO admins (adminID, requestID, status_req, payment_status, messageID, date) VALUES (?, ?, ?, ?, ?, ?)",
            (admin_id, request_id, status_req, payment_status, message_id, date)
        )
    connection.close()


def get_admin_by_column(column, val, *args):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()

    columns = ", ".join(args) if args else "*"
    query = f"SELECT {columns} FROM admins WHERE {column} = ?"

    cursor.execute(query, (val,))
    result = cursor.fetchone()
    connection.close()
    return result


def update_admin(col_name, col_val, param, param_val):
    connection = sqlite3.connect(db)
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"UPDATE admins SET {col_name} = ? WHERE {param} = ?", (col_val, param_val)
        )
        connection.commit()
    except sqlite3.OperationalError as e:
        print(f"Error updating the database: {e}")
    finally:
        connection.close()



def insert_order(request_id, is_confirmed, is_paid, admin_id, date):
    connection = sqlite3.connect(db)
    with connection:
        connection.execute("INSERT INTO orders (request_id, is_confirmed, is_paid, adminID, date) VALUES (?, ?, ?, ?, ?)",
            (request_id, is_confirmed, is_paid, admin_id, date))
    connection.close()


def get_orders(request_id):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT * FROM orders WHERE request_id=?", (request_id,))
        result = cursor.fetchall()

    except sqlite3.Error as e:
        print(f"Error retrieving data: {e}")
        result = []

    finally:
        connection.close()

    return result


def get_orders_by_column(column, val, *args):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()

    columns = ", ".join(args) if args else "*"
    query = f"SELECT {columns} FROM orders WHERE {column} = ?"

    cursor.execute(query, (val,))
    result = cursor.fetchone()
    connection.close()

    return result


def update_orders(col_name, col_val, param, param_val):
    connection = sqlite3.connect(db)
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"UPDATE orders SET {col_name} = ? WHERE {param} = ?", (col_val, param_val)
        )
        connection.commit()
    except sqlite3.OperationalError as e:
        print(f"Error updating the database: {e}")
    finally:
        connection.close()



def get_request_by_column(column, val, *args):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()

    columns = ", ".join(args) if args else "*"
    query = f"SELECT {columns} FROM requests WHERE {column} = ?"

    cursor.execute(query, (val,))
    result = cursor.fetchone()
    connection.close()

    return result


def get_requests_all(vin):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT * FROM requests WHERE vin = ?",
        (vin,)
    )
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()

    return columns, rows


def get_request_by_column_all(column, val, *args):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()

    columns = ", ".join(args) if args else "*"
    query = f"SELECT {columns} FROM requests JOIN orders o ON o.request_id = r.id WHERE {column} = ?"

    cursor.execute(query, (val,))
    columns_name = [description[0] for description in cursor.description]

    result = cursor.fetchall()
    return columns_name, result


def get_requests_ordered():
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT o.order_id, r.model, r.vin FROM requests r
        JOIN orders o ON o.request_id = r.id
        JOIN admins a ON a.requestID = r.id
        WHERE a.is_completed = 1
        """
    )
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    return columns, rows


def check_status(vin):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT status FROM requests WHERE vin = ?",
        (vin,)
    )
    connection.commit()
    result = cursor.fetchone()
    connection.close()
    return result


def update_request(col_name, col_val, param, param_val):
    connection = sqlite3.connect(db)
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"UPDATE requests SET {col_name} = ? WHERE {param} = ?", (col_val, param_val)
        )
        connection.commit()
    except sqlite3.OperationalError as e:
        print(f"Error updating the database: {e}")
    finally:
        connection.close()

def delete_request(user_id):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM requests WHERE issuerID = ? and status = 'Cancelled'",
        (user_id,)
    )
    connection.commit()
    connection.close()


def all_orders_info(req_id):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    query = """
        SELECT r.id, r.model, r.plateNumber, r.vin, r.last_price, r.vat, r.phoneNumber, r.paidprice, 
                r.documents, o.rate, o.kfee, o.overseasfee, r.date, r.username, r.percentage, r.vat_percentage, r.vat_price
        FROM requests r
        JOIN orders o ON o.request_id = r.id
        WHERE o.order_id = ?
    """

    cursor.execute(query, (req_id,))  # Corrected tuple syntax
    result = cursor.fetchall()  # Get all data

    columns = [desc[0] for desc in cursor.description]

    connection.close()

    return columns, result


def status_query(req_id):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    query = """
        SELECT o.kfee, o.overseasfee, o.rate, a.is_completed
            FROM orders o
            JOIN admins a ON a.requestID = o.request_id
            WHERE o.request_id = ?
    """

    cursor.execute(query, (req_id,))
    result = cursor.fetchall()

    columns = [desc[0] for desc in cursor.description]

    connection.close()

    return columns, result


def update_table(table, column, new_value, key_column, key_value):
    conn = sqlite3.connect(db)
    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {table} SET {column} = ? WHERE {key_column} = ?", (new_value, key_value))
        conn.commit()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()


def insert_comments(req_id, admin_id, username, comment):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO comments (request_id, adminID, username, comment) VALUES (?, ?, ?, ?)
    """, (req_id, admin_id, username, comment))
    connection.commit()
    connection.close()


def get_comments(req_id):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute("""
        SELECT username, comment FROM comments WHERE request_id = ?
    """, (req_id,))
    result = cursor.fetchall()
    connection.close()
    return result
