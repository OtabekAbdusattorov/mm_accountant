import sqlite3

db = 'account'

def create_table():
    connection = sqlite3.connect(db)  # Using consistent database name
    with connection:


        ## userstates table
        connection.execute("""
        CREATE TABLE IF NOT EXISTS userStates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            state TEXT,
            date TEXT
        )
        """)


        ## requests table
        connection.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model TEXT,
            vin TEXT,
            plateNumber TEXT,
            last_price REAL,
            paidprice REAL,
            vat REAL,
            phoneNumber TEXT,
            issuerID INTEGER,
            username TEXT,
            messageID INTEGER,
            status TEXT,
            documents BOOLEAN DEFAULT 0,
            date TEXT
        )
        """)


        ## orders table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                is_confirmed BOOLEAN DEFAULT 0,
                is_paid TEXT DEFAULT 'pending',
                adminID INTEGER,
                date TEXT,
                rate INTEGER,
                FOREIGN KEY (request_id) REFERENCES requests(id)
        )
        """)


        ## admin table to store admin activity
        connection.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adminID INTEGER,
                requestID INTEGER,
                status_req TEXT,
                payment_status TEXT DEFAULT 'pending',
                messageID INTEGER,
                is_completed BOOLEAN DEFAULT 0,
                date TEXT,
                FOREIGN KEY (requestID) REFERENCES requests(id)
        )
        """)


        ## temp table to store temp data (requests)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS temp_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                model TEXT,
                vin TEXT UNIQUE,
                plate_number TEXT UNIQUE,
                last_price REAL,
                vat REAL,
                phoneNumber TEXT
        )
        """)


    ## connection closed
    connection.close()