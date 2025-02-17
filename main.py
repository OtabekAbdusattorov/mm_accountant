from dotenv import load_dotenv
from datetime import datetime
import telebot, sqlite3, logging, os, send_file_pic as sfp
from telebot.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup


# Environmental variables initialization
load_dotenv()
bot_token = os.getenv("BOT_TOKEN")
admin_ids_str  = os.getenv("ADMIN_IDS")
admin_ids = [int(ID.strip()) for ID in admin_ids_str.split(',')]

# Variable related to database
db = "account"

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# TIME
time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# Bot initialization
bot = telebot.TeleBot(bot_token)

## Function create all necessary tables
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
            Model TEXT,
            VIN TEXT,
            Plate_Number TEXT,
            Last_Price REAL,
            VAT REAL,
            last_modify_userID INTEGER,
            username TEXT
        )
        """)


        ## orders table
        connection.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER,
                is_confirmed BOOLEAN DEFAULT 0,
                is_paid TEXT DEFAULT 'pending',
                last_modify_userID INTEGER,
                FOREIGN KEY (request_id) REFERENCES requests(id)
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
                vat REAL
        )
        """)


    ## connection closed
    connection.close()

create_table()


###### CLASS STATE MANAGER ######
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
        connection.close()

    def user_state(self, message, new_state):
        """Update or insert a user state based on their last known state."""
        user_id = message.from_user.id
        self.user_states[message.chat.id] = new_state

        current_state = self.get_state(user_id)
        if not current_state:
            self.insert_state(user_id, new_state)
        else:
            self.update_state(user_id, new_state)

state_manager = UserStateManager(db)


###### CLASS TEMP TABLE MANAGER ######
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
        connection = sqlite3.connect(db)
        with connection:
            connection.execute(
                f"UPDATE temp_requests SET {column} = ? WHERE user_id = ?", (value, user_id)
            )

    def get_temp_results(self, user_id):
        connection = sqlite3.connect(self.db)
        cursor = connection.cursor()
        cursor.execute(
            "SELECT Model, VIN, Plate_Number, Last_Price, VAT FROM temp_requests WHERE user_id = ?",
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
        """Check if a VIN already exists in the temp table."""
        connection = sqlite3.connect(self.db)
        cursor = connection.cursor()
        cursor.execute("SELECT vin FROM requests WHERE vin = ?", (vin,))
        exists = cursor.fetchone() is not None
        connection.close()
        return exists

temp_manager = TempTableManager(db)


## user input for temporary/instant store
user_data = {}

### Full access admin
def is_full_admin(user_id):
    return user_id in admin_ids


## get the infos from requests table
def get_requests_results(last_modify_userID):
    connection = sqlite3.connect(db)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT Model, VIN, Plate_Number, Last_Price, VAT, username, last_modify_userID FROM requests WHERE last_modify_userID = ?",
        (last_modify_userID,)
    )
    result = cursor.fetchone()
    connection.close()
    return result

# START page
@bot.message_handler(commands=['start'])
def start(message):
    state_manager.user_state(message, "start_menu")

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    full_list = KeyboardButton("Full list")
    send_request = KeyboardButton("Send request")
    keyboard.row(full_list, send_request)
    bot.send_message(message.chat.id,"Welcome! Please choose an option below:" ,reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "Full list")
def full_list(message):
    if is_full_admin(message.chat.id):
        screenshot_files = sfp.take_screenshot_of_data_for_admin()

        if screenshot_files:
            try:
                for screenshot_file in screenshot_files:
                    with open(screenshot_file, 'rb') as file:
                        bot.send_photo(message.chat.id, file)
            except Exception as e:
                print(f"Error sending screenshot: {e}")
                bot.send_message(message.chat.id, "Failed to generate the screenshot. Please try again later.")
        else:
            bot.send_message(message.chat.id, "No data found for your requests.")
    else:
        last_modify_userID = message.chat.id

        # Generate screenshot for the user's requests
        screenshot_files = sfp.take_screenshot_of_data_for_user(last_modify_userID)

        if screenshot_files:
            try:
                for screenshot_file in screenshot_files:
                    with open(screenshot_file, 'rb') as file:
                        bot.send_photo(message.chat.id, file)
            except Exception as e:
                print(f"Error sending screenshot: {e}")
                bot.send_message(message.chat.id, "Failed to generate the screenshot. Please try again later.")
        else:
            bot.send_message(message.chat.id, "You don't have any requests.")


@bot.message_handler(func=lambda message: message.text == "Send request")
def send_request(message):
    user_id = message.from_user.id
    user_data[user_id] = {}

    ## user in temp table
    temp_manager.insert_user(user_id)

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    bot.send_message(message.chat.id,"Enter the model name:\ne.g:\nVolkswagen Touareg,\nMercedes-AMG CLS63,\nKia Carnival" ,reply_markup=keyboard)
    state_manager.user_state(message, "enter_model")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_model")
def enter_model(message):
    user_id = message.from_user.id

    ## update on temp table
    temp_manager.update_temp_results(user_id, "model", message.text.strip())

    bot.send_message(message.chat.id, "Enter the VIN number:")
    state_manager.user_state(message, "enter_vin")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_vin")
def enter_vin(message):
    user_id = message.from_user.id

    if temp_manager.vin_exists(message.text.strip()):
            bot.send_message(message.chat.id, "Don't play with me mthrf**r! You used this vin number already!")
    else:
        ## update on temp table
        temp_manager.update_temp_results(user_id, "vin", message.text.strip())
        bot.send_message(message.chat.id, "Enter the Plate Number:")
        state_manager.user_state(message, "enter_plate")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_plate")
def enter_plate(message):
    user_id = message.from_user.id

    ## update on temp table
    temp_manager.update_temp_results(user_id, "plate_number", message.text.strip())

    bot.send_message(message.chat.id, "Enter the Last Price:")
    state_manager.user_state(message, "enter_price")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_price")
def enter_price(message):
    user_id = message.from_user.id
    try:
        ## update on temp table
        temp_manager.update_temp_results(user_id, "last_price", float(message.text.strip()))

        bot.send_message(message.chat.id, "Enter VAT:")
        state_manager.user_state(message, "enter_vat")
    except ValueError:
        bot.send_message(message.chat.id, "Invalid price. Please enter a number:")
        state_manager.user_state(message, "enter_price")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_vat")
def enter_vat(message):
    user_id = message.from_user.id
    try:
        # Update VAT in the temp table
        vat_value = float(message.text.strip())
        temp_manager.update_temp_results(user_id, "vat", vat_value)

        # Fetch all user data from the temp table for review
        car_info = temp_manager.get_temp_results(user_id)

        # Prepare a summary message
        if car_info:
            model, vin, plate_number, last_price, vat = car_info  # Assuming the tuple has these values
            summary_message = (
                f"Here is the information you entered:\n\n"
                f"Model: <b>{model}</b>\n"
                f"VIN: <b>{vin}</b>\n"
                f"Plate Number: <b>{plate_number}</b>\n"
                f"Last Price: <b>{last_price}</b>\n"
                f"VAT: <b>{vat}</b>\n\n"
                "Is everything correct?"
            )
        else:
            summary_message = "See. It is not working now. Ahhh, shh..."

        # Create the confirmation and cancel buttons
        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        confirm_button = InlineKeyboardButton("Confirm ✅", callback_data="confirm")
        cancel_button = InlineKeyboardButton("Cancel ❌", callback_data="cancel")
        inline_keyboard.add(confirm_button, cancel_button)

        # Send the summary and ask for confirmation with inline buttons
        bot.send_message(message.chat.id, summary_message, reply_markup=inline_keyboard, parse_mode="HTML")
        state_manager.user_state(message, "awaiting_confirmation")

    except ValueError:
        bot.send_message(message.chat.id, "Oh my my my....! Please enter a valid number. You are not buying Mars."
                                          "\nIt is just a car:")
        state_manager.user_state(message, "enter_vat")


@bot.callback_query_handler(func=lambda call: call.data == "confirm")
def handle_confirmation(call):
    user_id = call.from_user.id

    ## get results from temp table
    car_info = temp_manager.get_temp_results(user_id)

    if car_info:
        model, vin, plate_number, last_price, vat = car_info
        username = call.message.chat.first_name

        # Insert the information into the actual `requests` table
        connection = sqlite3.connect(db)
        with connection:
            connection.execute("""
                INSERT INTO requests (last_modify_userID, username, Model, VIN, Plate_Number, Last_Price, VAT)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username, model, vin, plate_number, last_price, vat))

        # Clear the temp table for the user after insertion
        temp_manager.clear_temp_request(user_id)

        # Send a confirmation message to the user
        bot.send_message(call.message.chat.id, "Your request has been successfully submitted. Thank you!")
        send_to_admins(username, user_id, model, vin, plate_number, last_price, vat)
        state_manager.update_state(call.message.chat.id, "start_menu")
    else:
        bot.send_message(call.message.chat.id, "Error has occurred. Please try again right now. It might work or not.")


@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def handle_cancellation(call):
    user_id = call.from_user.id

    # Clear the temp table for the user (cancel the current process)
    temp_manager.clear_temp_request(user_id)

    bot.send_message(call.message.chat.id, "Your request has been canceled. No thank you!")

    # Optionally, move the user to a new state (e.g., back to main menu)
    state_manager.update_state(call.message.chat.id, "start_menu")


def send_to_admins(username, last_modify_userID, model, vin, plate_number, last_price, vat):

    admin_summary_message = (
                f"Here is the information that has been entered by {username}:\n\n"
                f"Model: <b>{model}</b>\n"
                f"VIN: <b>{vin}</b>\n"
                f"Plate Number: <b>{plate_number}</b>\n"
                f"Last Price: <b>{last_price}</b>\n"
                f"VAT: <b>{vat}</b>\n\n"
                f"User ID: {last_modify_userID}"
    )

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    confirm_button = InlineKeyboardButton("Confirm ✅", callback_data="confirm_by_admin")
    cancel_button = InlineKeyboardButton("Cancel ❌", callback_data="cancel_by_admin")
    edit_button = InlineKeyboardButton("Edit 🖋️", callback_data="edit_by_admin")
    inline_keyboard.add(confirm_button, cancel_button)
    inline_keyboard.add(edit_button)

    for admin in admin_ids:
        sent_message = bot.send_message(admin, admin_summary_message, reply_markup=inline_keyboard, parse_mode="HTML")
        bot.pin_chat_message(admin, sent_message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == "confirm_by_admin")
def handle_confirmation_by_admin(call):
    message_text = call.message.text
    user_id_line = [line for line in message_text.split('\n') if line.startswith("User ID:")]
    if user_id_line:
        last_modify_userID = user_id_line[0].split("User ID: ")[1]


    for admin in admin_ids + [last_modify_userID]:
        bot.send_message(admin, f"Request has been confirmed by {call.message.chat.first_name}, and it is ready for payment.")
    bot.send_message(call.message.chat.id, "You have confirmed that every data is correct and ready for payment. Thank you!")
    bot.answer_callback_query(call.id, "Confirmed ✅")


@bot.callback_query_handler(func=lambda call: call.data == "cancel_by_admin")
def handle_cancel_by_admin(call):
    message_text = call.message.text
    user_id_line = [line for line in message_text.split('\n') if line.startswith("User ID:")]
    username = ''
    last_modify_userID = ''

    if user_id_line:
        last_modify_userID = user_id_line[0].split("User ID: ")[1]

    issue_owner = get_requests_results(last_modify_userID)

    if issue_owner:
        username = issue_owner[5]

    for admin in admin_ids:
        bot.send_message(admin, f"Request has been cancelled by {call.message.chat.first_name}, and it will be returned to the {username}.\n\nExplain the reason (mandatory): ")

if __name__ == '__main__':
    bot.infinity_polling()