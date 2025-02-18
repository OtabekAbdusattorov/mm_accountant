import sqlite3

db = 'account'

def insert_order(request_id, is_confirmed, is_paid, admin_id):
    connection = sqlite3.connect(db)
    with connection:
        connection.execute("INSERT INTO orders (request_id, is_confirmed, is_paid, adminID) VALUES (?, ?, ?, ?)", (request_id, is_confirmed, is_paid, admin_id,))
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


def get_request_by_vin(vin):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id FROM requests WHERE vin = ?",
        (vin,)
    )
    result = cursor.fetchone()
    connection.close()
    return result


## get the infos from requests table
def get_requests_results(issue_by):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT Model, VIN, PlateNumber, Last_Price, VAT, username, last_modify_userID FROM requests WHERE last_modify_userID = ?",
        (issue_by,)
    )
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


def update_request(col_name, val, user_id):
    try:
        connection = sqlite3.connect(db)
        cursor = connection.cursor()

        print(f"Executing update query...")
        cursor.execute(
            f"UPDATE requests SET {col_name} = ? WHERE last_modify_userID = ?", (val, user_id)
        )
        connection.commit()

        print(f"Update successful for {col_name}")
    except sqlite3.OperationalError as e:
        print(f"Error updating the database: {e}")
    finally:
        connection.close()