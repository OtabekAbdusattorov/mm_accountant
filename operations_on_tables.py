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
            (request_id, is_confirmed, is_paid, admin_id, date,))
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


def get_request_by_column_ordered(column, val, *args):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()

    columns = ", ".join(args) if args else "*"
    query = f"SELECT r.{columns} FROM requests r JOIN orders o ON o.request_id = r.id WHERE {column} = ?"

    cursor.execute(query, (val,))
    result = cursor.fetchone()
    connection.close()

    return result


def get_requests_all(vin=None):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    if vin is None:
        cursor.execute(
            "SELECT * FROM requests"
        )
    else:
        cursor.execute(
            "SELECT * FROM requests WHERE vin = ?",
            (vin,)
        )
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    return columns, rows


def  get_request_by_column_all(column, val, *args):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()

    columns = ", ".join(args) if args else "*"
    query = f"SELECT {columns} FROM requests WHERE {column} = ?"

    cursor.execute(query, (val,))
    columns_name = [description[0] for description in cursor.description]

    result = cursor.fetchall()
    return columns_name, result


def get_requests_all_ordered(vin=None):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    if vin is None:
        cursor.execute(
            "SELECT r.* FROM requests r JOIN orders o ON o.request_id = r.id"
        )
    else:
        cursor.execute(
            "SELECT r.* FROM requests r JOIN orders o ON o.request_id = r.id WHERE r.vin = ?",
            (vin,)
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
        SELECT r.model, r.plateNumber, r.vin, r.last_price, r.vat, r.phoneNumber, r.paidprice, 
                r.documents, o.rate, o.kfee, o.overseasfee, r.date, r.username
        FROM requests r
        JOIN orders o ON o.request_id = r.id
        WHERE r.id = ?
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


def update_balance(price, user_id):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute(
        f"UPDATE userStates SET balance = ? WHERE user_id = ?", (price, user_id)
    )
    connection.commit()
    connection.close()


def get_balance(user_id=None):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()

    if user_id is None:
        # Fetch all balances if user_id is None (admin mode)
        query = "SELECT balance, user_id FROM userStates"
        cursor.execute(query)
        result = cursor.fetchall()  # Fetch all rows as a list of tuples
    else:
        # Fetch the balance for a specific user
        query = "SELECT balance, user_id FROM userStates WHERE user_id = ?"
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()  # Fetch one record (tuple) for the specific user

    connection.close()

    return result  # Will return a tuple for one user or a list of tuples for all users