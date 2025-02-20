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

