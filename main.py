import math
import threading
from dotenv import load_dotenv
from datetime import datetime
import telebot \
    , sqlite3 \
    , logging \
    , pytz \
    , os \
    , send_file_pic as sfp \
    , userState \
    , createQueries as cQ \
    , tempTableManager as tTM \
    , operations_on_tables as oot \
    , page_navigation as pg_nav \
    , re \
    , manage_documents as md
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
timezone = pytz.timezone('Asia/Seoul')
time = datetime.now().strftime("%d/%m/%Y %H:%M")

# Bot initialization
bot = telebot.TeleBot(bot_token)

## Function create all necessary tables
cQ.create_table()


###### STATE MANAGER ######
state_manager = userState.UserStateManager(db)


###### CLASS TEMP TABLE MANAGER ######
temp_manager = tTM.TempTableManager(db)


## pinned messages = []
msg_ids = {}

## last request info
user_last_request_info = {}


### Full access admin
def is_full_admin(user_id):
    return user_id in admin_ids


user_last_message = {}

def delete_last_message(chat_id):
    """Deletes the last message of the user if exists."""
    if chat_id in user_last_message:
        try:
            bot.delete_message(chat_id, user_last_message[chat_id])
        except Exception as e:
            print(f"Error deleting message: {e}")
        del user_last_message[chat_id]



# START page
@bot.message_handler(commands=['start'])
def start(message):
    state_manager.user_state(message, "start_menu")

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    full_lists = KeyboardButton("Full list")
    send_requests = KeyboardButton("Send request")
    keyboard.row(full_lists, send_requests)
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
        last_modify_user_id = message.chat.id

        # Generate screenshot for the user's requests
        screenshot_files = sfp.take_screenshot_of_data_for_user(last_modify_user_id)

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

    ## user in temp table
    temp_manager.insert_user(user_id)

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    sent_msg = bot.send_message(message.chat.id,"Enter the model name:\ne.g:\nVolkswagen Touareg,\nMercedes-AMG CLS63,\nKia Carnival", reply_markup=keyboard)
    user_last_message[message.chat.id] = sent_msg.message_id
    bot.delete_message(message.chat.id, message.message_id)
    state_manager.user_state(message, "enter_model")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_model")
def enter_model(message):
    user_id = message.from_user.id

    delete_last_message(message.chat.id)

    ## update on temp table
    temp_manager.update_temp_results(user_id, "model", message.text.strip())

    sent_msg = bot.send_message(message.chat.id, "Enter the plate number:")
    user_last_message[message.chat.id] = sent_msg.message_id
    bot.delete_message(message.chat.id, message.message_id)
    state_manager.user_state(message, "enter_plate")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_plate")
def enter_plate(message):
    user_id = message.from_user.id

    delete_last_message(message.chat.id)

    ## update on temp table
    temp_manager.update_temp_results(user_id, "plate_number", message.text.strip())

    sent_msg = bot.send_message(message.chat.id, "Enter the VIN:")
    user_last_message[message.chat.id] = sent_msg.message_id
    bot.delete_message(message.chat.id, message.message_id)
    state_manager.user_state(message, "enter_vin")


def is_valid_vin(vin):
    vin_pattern = r"^[A-Z0-9]{17}$"
    return re.fullmatch(vin_pattern, vin) is not None

@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_vin")
def enter_vin(message):
    user_id = message.from_user.id

    delete_last_message(message.chat.id)

    try:
        vin = message.text.strip()
        if not is_valid_vin(vin):
            sent_msg = bot.send_message(message.chat.id,"Invalid VIN. Enter valid VIN 🚫")
            state_manager.user_state(message, "enter_vin")
        else:
            if temp_manager.vin_exists(vin):
                sent_msg = bot.send_message(message.chat.id, "Don't play with me, motherfucker! You used this VIN number already! 🚫")
                state_manager.user_state(message, "enter_vin")
            else:
                temp_manager.update_temp_results(user_id, "vin", vin)
                sent_msg = bot.send_message(message.chat.id, "Enter last price:")
                state_manager.user_state(message, "enter_price")
        user_last_message[message.chat.id] = sent_msg.message_id
        bot.delete_message(message.chat.id, message.message_id)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An error occurred: {str(e)}")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_price")
def enter_price(message):
    user_id = message.from_user.id

    delete_last_message(message.chat.id)

    try:
        temp_manager.update_temp_results(user_id, "last_price", float(message.text.strip()))

        sent_msg = bot.send_message(message.chat.id, "Enter VAT:")
        user_last_message[message.chat.id] = sent_msg.message_id
        bot.delete_message(message.chat.id, message.message_id)
        state_manager.user_state(message, "enter_vat")
    except ValueError:
        sent_msg = bot.send_message(message.chat.id, "Invalid price. Please enter a number:")
        user_last_message[message.chat.id] = sent_msg.message_id
        bot.delete_message(message.chat.id, message.message_id)
        state_manager.user_state(message, "enter_price")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_vat")
def enter_vat(message):
    user_id = message.from_user.id

    delete_last_message(message.chat.id)

    try:
        # Update VAT in the temp table
        vat_value = message.text.strip()

        temp_manager.update_temp_results(user_id, "vat_value", float(vat_value))

        sent_msg = bot.send_message(message.chat.id, "Enter dealer name and phone number:")
        user_last_message[message.chat.id] = sent_msg.message_id
        bot.delete_message(message.chat.id, message.message_id)
        state_manager.user_state(message, "enter_dealer")


    except ValueError:
        bot.send_message(message.chat.id, "Oh my my my....! Please enter a valid number. You are not buying Mars."
                                          "\nIt is just a car:")
        state_manager.user_state(message, "enter_vat")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_dealer")
def enter_dealer_phone(message):
    user_id = message.from_user.id

    delete_last_message(message.chat.id)

    temp_manager.update_temp_results(user_id, "phoneNumber", message.text.strip())
    bot.delete_message(message.chat.id, message.message_id)
    state_manager.user_state(message, "summary_request")
    summary_request(message)


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "summary_request")
def summary_request(message):
    car_info = temp_manager.get_temp_results(message.chat.id)

    if car_info:
        model, vin, plate_number, last_price, vat, phone_number = car_info
        summary_message = (
            f"Here is the information you entered:\n\n"
            f"Model: <b>{model}</b>\n"
            f"Plate Number: <b>{plate_number}</b>\n"
            f"VIN: <b>{vin}</b>\n"
            f"Last Price: <b>{last_price:,}₩</b>\n"
            f"VAT: <b>{vat:,}₩</b>\n"
            f"Dealer phone number: <b>{phone_number}</b>\n"
            f"Date: <b>{time}</b>\n\n"
            "Is everything correct?"
        )
    else:
        summary_message = "See. It is not working now. Ahhh, shh..."

    # Create the confirmation and cancel buttons
    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    confirm_button = InlineKeyboardButton("Confirm ✅", callback_data="confirm")
    cancel_button = InlineKeyboardButton("Cancel ❌", callback_data="cancel")
    edit_button = InlineKeyboardButton("Edit 🖋️", callback_data="edit")
    inline_keyboard.add(confirm_button, cancel_button)
    inline_keyboard.add(edit_button)

    # Send the summary and ask for confirmation with inline buttons
    sent_msg = bot.send_message(message.chat.id, summary_message, reply_markup=inline_keyboard, parse_mode="HTML")

    user_last_message[message.chat.id] = sent_msg.message_id

    user_last_request_info[message.chat.id] = sent_msg.message_id

    state_manager.user_state(message, "awaiting_confirmation")


@bot.callback_query_handler(func=lambda call: call.data == "edit")
def handle_edit_request(call):
    user_id = call.message.chat.id

    # Define editable fields
    editable_fields = [
        {"number": 1, "display": "Model Name", "key": "model"},
        {"number": 2, "display": "Plate Number", "key": "plate_number"},
        {"number": 3, "display": "VIN", "key": "vin"},
        {"number": 4, "display": "Last Price", "key": "last_price"},
        {"number": 5, "display": "VAT", "key": "vat"},
        {"number": 6, "display": "Dealer Phone Number", "key": "phoneNumber"}
    ]

    # Generate selection message
    message_text = "Select the field you want to edit:\n\n"
    for field in editable_fields:
        message_text += f"{field['number']}. {field['display']}\n"

    # Create inline keyboard for selecting fields
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = [InlineKeyboardButton(str(field["number"]), callback_data=f"edit_user_field_{field['key']}") for field in editable_fields]
    keyboard.add(*buttons)

    # Send selection message
    sent_msg = bot.send_message(user_id, message_text, reply_markup=keyboard)
    user_last_message[user_id] = sent_msg.message_id
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_user_field_"))
def handle_edit_field(call):
    user_id = call.message.chat.id
    field_key = call.data.split("_")[3]

    delete_last_message(user_id)

    state_manager.user_state(call.message, f"editing_{field_key}")

    sent_msg = bot.send_message(user_id, f"Enter the new value for {field_key.replace('_', ' ').title()}:")
    user_last_message[user_id] = sent_msg.message_id

    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: state_manager.get_state(message.chat.id).startswith("editing_"))
def handle_edit_value_input(message):
    user_id = message.chat.id
    field_key = state_manager.get_state(user_id).split("_")[1]
    new_value = message.text.strip()

    delete_last_message(user_id)

    field_key = "plate_number" if field_key == "plate" else field_key
    field_key = "vat_value" if field_key == "vat" else field_key
    field_key = "last_price" if field_key == "last" else field_key

    bot.delete_message(user_id, message.message_id)
    if field_key == "vin":
        if not is_valid_vin(message.text):
            bot.send_message(message.chat.id,
                         "❌ Invalid VIN! It must be exactly 17 characters long and contain only uppercase letters and numbers.")
            return
    if field_key in ["last_price", "vat"]:
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ Invalid input! Please enter a valid number for the price.")
            return
    else:
        temp_manager.update_temp_results(user_id, field_key, new_value)

        state_manager.user_state(message, "summary_request")
        if user_id in user_last_request_info:
            try:
                bot.delete_message(user_id, user_last_request_info[user_id])
            except Exception as e:
                print(f"Error deleting previous order details message: {e}")
            finally:
                del user_last_request_info[user_id]
        summary_request(message)


@bot.callback_query_handler(func=lambda call: call.data == "confirm")
def handle_confirmation(call):

    user_id = call.message.chat.id

    ## get results from temp table
    car_info = temp_manager.get_temp_results(user_id)

    message_text = call.message.text
    vin = None
    vin_num = [line for line in message_text.split('\n') if line.startswith("VIN:")]
    if vin_num:
        vin = vin_num[0].split("VIN: ")[1]

    status = oot.get_request_by_column("vin", vin, "status")

    if status:
        bot.send_message(call.message.chat.id, "This request has already been confirmed and sent to admins.")
    else:
        if car_info:
            model, vin, plate_number, last_price, vat_price, phone_number = car_info
            username = call.message.chat.first_name

            vat_perc = vat_price / 11

            vat_value = math.floor(vat_perc + 0.5)

            connection = sqlite3.connect(db)
            with connection:
                connection.execute("""
                    INSERT INTO requests (model, vin, platenumber, last_price, vat, vat_price, issuerID, username, messageID, date, phoneNumber, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (model, vin, plate_number, last_price, vat_value, vat_price, user_id, username, call.message.message_id, time, phone_number, "Confirmed"))
            connection.close()

            # Clear the temp table for the user after insertion
            temp_manager.clear_temp_request(user_id)

            # Send a confirmation message to the user

            bot.send_message(call.message.chat.id, "Your request has been successfully submitted. Thank you!")

            req_id = oot.get_request_by_column("vin", vin, "id")[0]

            send_to_admins(username, model, vin, plate_number, last_price, vat_price, vat_value, phone_number, req_id, time)
            state_manager.user_state(call.message, "start_menu")
        else:
            bot.answer_callback_query(call.id, "Error has occurred. Please try again right now. It might work or not.")


@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def handle_cancellation(call):
    user_id = call.from_user.id

    # Clear the temp table for the user (cancel the current process)
    temp_manager.clear_temp_request(user_id)

    bot.delete_message(call.message.chat.id, call.message.message_id)

    sent_msg = bot.send_message(call.message.chat.id, "Your request has been canceled. No thank you!")
    user_last_message[call.message.chat.id] = sent_msg.message_id

    delete_last_message(user_id)

    # Optionally, move the user to a new state (e.g., back to main menu)
    state_manager.user_state(call.message, "start_menu")


def send_to_admins(username, model, vin, plate_number, last_price, vat_price, vat, phone_number, req_id, date):

    admin_summary_message = (
                f"Here is the information that has been entered by {username}:\n\n"
                f"Model: <b>{model}</b>\n"
                f"Plate Number: <b>{plate_number}</b>\n"
                f"VIN: <b>{vin}</b>\n"
                f"Last Price: <b>{last_price:,}₩</b>\n"
                f"VAT: <b>{vat_price:,}₩</b>\n"
                f"VAT Amount: <b>{vat:,}₩</b>\n"
                f"Dealer phone number: <b>{phone_number}</b>\n"
                f"Requested date: <b>{date}</b>\n\n"
                f"Request ID: {req_id}\n"
    )

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    cookie_button = InlineKeyboardButton("Cookie sharing 🍪", callback_data=f"percent_by_admin|{req_id}")
    confirm_button = InlineKeyboardButton("Confirm ✅", callback_data="confirm_by_admin")
    cancel_button = InlineKeyboardButton("Cancel ❌", callback_data=f"cancel_by_admin|{vin}")
    edit_button = InlineKeyboardButton("Edit 🖋️", callback_data="edit_by_admin")
    inline_keyboard.add(cookie_button)
    inline_keyboard.add(confirm_button, cancel_button)
    inline_keyboard.add(edit_button)

    for admin in admin_ids:
        sent_message = bot.send_message(admin, admin_summary_message, reply_markup=inline_keyboard, parse_mode="HTML")
        msg_ids[admin] = sent_message.message_id
        bot.pin_chat_message(admin, sent_message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("percent_by_admin|"))
def percent_by_admin(call):
    user_id = call.message.chat.id

    callback_data_parts = call.data.split("|")
    req_id = callback_data_parts[1]

    bot.send_message(user_id, "Percentage of the cookie you want to share: (e.g: 30 or 70)")
    bot.register_next_step_handler(call.message, handler_percent_by_admin, req_id, call)


def handler_percent_by_admin(message, req_id, call):
    perc_val = int(message.text)

    state_manager.user_state(message, "cookie_by_admin")

    oot.update_request(col_name="percentage", col_val=perc_val, param="id", param_val=req_id)

    vat = oot.get_request_by_column("id", req_id, "vat")[0]

    vat_perc = (vat * perc_val) / 100

    oot.update_request(col_name="vat_percentage", col_val=vat_perc, param="id", param_val=req_id)

    oot.update_admin(col_name="status_req", col_val="Cookie", param="requestID", param_val=req_id)

    bot.answer_callback_query(call.id, "Yeah boy, noiice! You can go on...")


@bot.callback_query_handler(func=lambda call: call.data == "confirm_by_admin")
def handle_confirmation_by_admin(call):
    state_manager.user_state(call.message, "confirm_by_admin")
    message_text = call.message.text

    vin = None
    vin_num = [line for line in message_text.split('\n') if line.startswith("VIN:")]
    if vin_num:
        vin = vin_num[0].split("VIN: ")[1]

    if not vin:
        bot.answer_callback_query(call.id, "❌ VIN not found in the message.")
        return

    query_result = oot.get_request_by_column("vin", vin, "issuerID", "id", "vat_percentage", "percentage", "vat")

    if not query_result:
        bot.answer_callback_query(call.id, f"❌ No request found for VIN: {vin}.")
        return

    issuer_id, req_id, vat_perc, perc, vat = query_result

    result_admin = oot.get_admin_by_column("requestID", req_id, "status_req")

    admin_id = call.message.chat.id

    last_price = oot.get_request_by_column("id", req_id, "last_price")[0]

    if perc is not None:
        if result_admin:
            status = result_admin[0]
            if status in ["Confirmed", "Cancelled"]:
                bot.answer_callback_query(call.id, "This request has been confirmed or cancelled.")
            else:
                after_vat_perc_price = math.floor((last_price - vat_perc) + 0.5)
                vat_share_admin = math.floor((vat - vat_perc) + 0.5)

                oot.update_admin(col_name="status_req", col_val="Confirmed", param="requestID", param_val=req_id)
                oot.update_admin(col_name="vat_percentage", col_val=vat_share_admin, param="requestID", param_val=req_id)
                oot.insert_order(req_id, 1, "Pending", admin_id, time, after_vat_perc_price)
                confirm_request(call, vin, req_id, issuer_id, after_vat_perc_price, perc)
        else:
            msg_id = msg_ids.get(admin_id)
            if req_id:
                after_vat_perc_price = math.floor((last_price - vat_perc) + 0.5)
                vat_share_admin = math.floor((vat - after_vat_perc_price) + 0.5)

                oot.insert_order(req_id, 1, "Pending", admin_id, time, after_vat_perc_price)
                oot.insert_admin(call.message.chat.id, req_id, "Confirmed", "Pending", msg_id, time, vat_share_admin)
                confirm_request(call, vin, req_id, issuer_id, after_vat_perc_price, perc)
    else:
        bot.answer_callback_query(call.id, "Broo, share a cookie. Don't be mean!")


def confirm_request(call, vin, req_id, issuer_id, vat_perc, perc):

    # Send confirmation message
    confirmed_message = f"Request (VIN: {vin}) has been confirmed by {call.message.chat.first_name}, and it is ready for payment."

    recipients = admin_ids if issuer_id in admin_ids else admin_ids + [issuer_id]
    for recipient in recipients:
        bot.send_message(recipient, text=confirmed_message)

    # Send payment button
    inline_keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Payment 💳️", callback_data=f"payment_user_{req_id}_{vin}")
    )
    bot.send_message(issuer_id,
                     text=f"This request (VIN: <b>{vin}</b>) has been confirmed, and ready for payment.\n"
                          f"Price you should pay after VAT share is <b>{vat_perc:,}₩</b>.\n"
                          f"Your share is <b>{perc}%</b>.\n"
                          f"💳 Payment status:\n⏳ PENDING...",
                     reply_markup=inline_keyboard,
                     parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_by_admin"))
def handle_cancel_by_admin(call):
    message_text = call.message.text

    callback_data_parts = call.data.split("|")
    vin = callback_data_parts[1] if len(callback_data_parts) > 1 else "Unknown"

    req_id = None
    req_id_num = [line for line in message_text.split('\n') if line.startswith("Request ID:")]
    if req_id_num:
        req_id = req_id_num[0].split("Request ID: ")[1]

    username, issuer_id = oot.get_request_by_column("id", req_id, "username", "issuerID")
    msg = bot.send_message(
                call.message.chat.id,
                f"Request (VIN: {vin} by {username}) has been cancelled by {call.message.chat.first_name}, and it will be returned to *{username}*.\n\n"
                f"Explain the reason (mandatory): ", parse_mode="Markdown")

    for admin in admin_ids:
        try:
            bot.delete_message(admin, msg_ids[admin])
        except Exception as e:
            if "message to delete not found" in str(e):
                continue
            else:
                continue
    bot.register_next_step_handler(msg, lambda message: process_cancellation_reason(message,issuer_id, vin, username))


def process_cancellation_reason(msg, issuer_id, vin, username):
    cancellation_reason = msg.text

    message_req_id = oot.get_request_by_column("issuerID", issuer_id, "messageID")[0]
    req_id = oot.get_request_by_column("issuerID", issuer_id, "id")[0]

    bot.send_message(issuer_id, f"❌ Your request (VIN: {vin}) has been cancelled, and is deleted by now.\n\n📌 *Reason:* {cancellation_reason}",
        parse_mode="Markdown")

    for admin in admin_ids:
        bot.send_message(admin, f"The request (VIN: {vin} by {username}) has been sent back to *{username}*. The reason that has been entered:\n\n*{cancellation_reason}*", parse_mode="Markdown")

        msg_id = oot.get_admin_by_column("requestID", req_id, "messageID")[0]

        try:
            for i in range(msg_id, msg.message_id + 1):
                try:
                    bot.delete_message(admin, i)
                except Exception as e:
                    if "message to delete not found" in str(e):
                        continue
                    else:
                        continue
        except Exception as e:
            print(f"General error while deleting messages for admin {admin}: {e}")

    try:
        bot.delete_message(issuer_id, message_req_id+1)
    except Exception as e:
        if "message to delete not found" in str(e):
            pass
        else:
            pass


def send_request_info(chat_id, vin):
    columns, req_one_data = oot.get_requests_all(vin)

    full_req_one_info, inline_keyboard = pg_nav.format_results(columns, req_one_data, context="requests_edit", user_id=chat_id)

    bot.send_message(
        chat_id=chat_id,
        text=f"Request Info:\n\n{full_req_one_info}",
        reply_markup=inline_keyboard,
        parse_mode='HTML'
    )



@bot.callback_query_handler(func=lambda call: call.data == "edit_by_admin")
def view_edit_requests_admin(call):
    state_manager.user_state(call.message, "view_edit_admin")

    message_text = call.message.text

    vin=None
    vin_num = [line for line in message_text.split('\n') if line.startswith("VIN:")]
    if vin_num:
        vin = vin_num[0].split("VIN: ")[1]

    req_id = None
    req_id_num = [line for line in message_text.split('\n') if line.startswith("Request ID:")]
    if req_id_num:
        req_id = req_id_num[0].split("Request ID: ")[1]

    result = oot.get_admin_by_column("requestID", req_id, "status_req")

    if result:
        if result[0] in ["Confirmed", "Cancelled"]:
            bot.answer_callback_query(call.id, "This request has been confirmed or cancelled.")
        else:
            send_request_info(call.message.chat.id, vin)
    else:
        send_request_info(call.message.chat.id, vin)


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_request_"))
def edit_request_callback(call):
    state_manager.user_state(call.message, "edit_request_admin")

    edit_index = call.data.split("_")[-2]

    if edit_index == "price":
        edit_index = "last_price"

    req_id = call.data.split("_")[-1]

    bot.send_message(call.message.chat.id, f"Edit the {edit_index}:")
    bot.register_next_step_handler(call.message, lambda msg: edit_value_handler(msg, edit_index, req_id, call))


def edit_value_handler(message, column, req_id, call):
    admin_id = message.chat.id
    msg_id = msg_ids.get(admin_id)

    if msg_id is None:
        bot.send_message(message.chat.id, "❌ Error: Cannot edit message. Message ID not found.")
        return

    # Validate VIN if editing VIN
    if column == "vin":
        if not is_valid_vin(message.text):
            bot.answer_callback_query(call.id, "❌ Invalid VIN! It must be exactly 17 characters long and contain only uppercase letters and numbers.")
            return

    # Validate price if editing price-related fields
    if column in ["last_price", "vat"]:
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ Invalid input! Please enter a valid number for the price.")
            return

    result = oot.get_admin_by_column("requestID", req_id, "status_req")

    if result:
        oot.update_admin(col_name='status_req', col_val="Edited", param="requestID", param_val=req_id)
    else:
        oot.insert_admin(admin_id, req_id, "Edited", "Pending", msg_id, time, 0)

    oot.update_request(col_name=f'{column}', col_val=message.text, param="id", param_val=req_id)
    message_id = oot.get_admin_by_column("requestID", req_id, "messageID")

    username, model, vin, plate_number, last_price, vat, vat_price, phone_number = (
        oot.get_request_by_column("id", req_id, "username", "model", "vin", "plateNumber", "last_price", "vat", "vat_price", "phoneNumber"))

    try:
        send_to_admins(username, model, vin, plate_number, last_price, vat_price, vat, phone_number, req_id, time)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error editing message: {e}")

    for admins in admin_ids:
        for i in range(message_id[0], message.message_id + 1):
            try:
                bot.delete_message(admins, i)
            except Exception as e:
                if "message to delete not found" in str(e):
                    continue
                else:
                    continue


@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_user"))
def payment_user(call):
    req_id = call.data.split("_")[-2]
    vin = call.data.split("_")[-1]

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    krw_button = InlineKeyboardButton("KRW", callback_data=f"method_krw_{req_id}_{vin}")
    usdt_button = InlineKeyboardButton("USDT", callback_data=f"method_usdt_{req_id}_{vin}")
    inline_keyboard.add(usdt_button, krw_button)

    bot.send_message(call.message.chat.id, "Please select the payment method and send the receipt or screenshot:", reply_markup=inline_keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("method_"))
def payment_method(call):
    method_type = call.data.split("_")[1]
    req_id = call.data.split("_")[2]
    vin = call.data.split("_")[3]

    # Create new keyboard with the selected option marked
    inline_keyboard = InlineKeyboardMarkup(row_width=2)

    # Add ❌ to the selected button
    krw_text = "KRW ✅" if method_type == "krw" else "KRW"
    usdt_text = "USDT ✅" if method_type == "usdt" else "USDT"

    # Keep the original callback_data to allow changing the selection
    krw_button = InlineKeyboardButton(krw_text, callback_data=f"method_krw_{req_id}_{vin}")
    usdt_button = InlineKeyboardButton(usdt_text, callback_data=f"method_usdt_{req_id}_{vin}")
    inline_keyboard.add(usdt_button, krw_button)

    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=inline_keyboard
    )

    oot.update_request(col_name="paid_type", col_val=method_type, param="id", param_val=req_id)

    bot.clear_step_handler(call.message)

    bot.register_next_step_handler(call.message, lambda msg: ask_for_price(msg, vin, call))


def ask_for_price(message, vin, call):
    if message.photo:
        picture = message.photo[-1].file_id

        # Get file details and download the image
        file_info = bot.get_file(picture)
        downloaded_file = bot.download_file(file_info.file_path)

        folder_path = 'content/payment_images'
        os.makedirs(folder_path, exist_ok=True)

        # Save the picture with a unique name (you can include the VIN in the filename)
        file_path = os.path.join(folder_path, f"{vin}_payment.jpg")
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)

        bot.send_message(message.chat.id, "Now, please send the price.")
        bot.register_next_step_handler(message, send_price, picture, vin)
    else:
        bot.answer_callback_query(call.id, "❌ Please send a valid picture... (again)")
        bot.register_next_step_handler(message, ask_for_price, vin)


def send_price(message, picture, vin):
    try:
        price = int(message.text)

        oot.update_request(col_name="paidprice", col_val=price, param="vin", param_val=vin)

        user_id, last_price, vat_percentage, paid_type = oot.get_request_by_column("vin", vin,
                        "issuerID", "last_price", "vat_percentage", "paid_type")

        balance = price - last_price


        last_balance_result = oot.get_balance(message.chat.id)
        if last_balance_result[0] is None:
            oot.update_balance(balance, user_id)
        else:
            last_balance, issuer_id = last_balance_result
            balance = last_balance + price - last_price
            oot.update_balance(balance, user_id)



        inline_keyboard = InlineKeyboardMarkup(row_width=2)
        exchange_rate_button = InlineKeyboardButton("Exchange rate 💰", callback_data=f"exchange_rate_{vin}")
        fees_korea_button = InlineKeyboardButton("Fees in Korea 🇰🇷", callback_data=f"fees_korea_{vin}")
        fees_overseas_button = InlineKeyboardButton("Overseas Fee 🌍", callback_data=f"fees_overseas_{vin}")
        payment_button = InlineKeyboardButton("Order completed ✅", callback_data=f"order_completed_{vin}")

        inline_keyboard.add(exchange_rate_button)
        inline_keyboard.add(fees_korea_button, fees_overseas_button)
        inline_keyboard.add(payment_button)

        username = oot.get_request_by_column("vin", vin, "username")[0]

        for admin_id in admin_ids:
            bot.send_photo(admin_id, picture)
            bot.send_message(
                admin_id,
                text=f"User ({username}) has confirmed the payment request for (VIN: {vin}). 💳\n\n"
                     f"Price, paid by user: <b>{price:,}</b> in <b>{paid_type.upper()}</b>\n"
                     f"VAT share: <b>{vat_percentage:,}₩</b>\n",
                reply_markup=inline_keyboard,
                parse_mode="HTML"
            )

        upload_keyboard = InlineKeyboardMarkup()
        upload_button = InlineKeyboardButton("Upload documents 📄", callback_data=f"upload_doc_{vin}")
        upload_keyboard.add(upload_button)

        bot.send_message(message.chat.id, f"Your payment details for (VIN: {vin}) have been sent to the admin 💼."
                                          f" Upload all related documents as images in the meantime!",
                                        reply_markup=upload_keyboard)

    except ValueError:
        bot.send_message(message.chat.id, "❌ Please enter a valid price. Please send the price again.")
        bot.register_next_step_handler(message, send_price, picture)


@bot.callback_query_handler(func=lambda call: call.data.startswith("fees_"))
def fees(call):
    """Handles fees input for Korea or Overseas."""
    vin = call.data.split("_")[-1]
    req_id = oot.get_request_by_column("vin", vin, "id")[0]
    result_rate = oot.get_orders_by_column("request_id", req_id, "rate")[0]

    if result_rate is None:
        bot.answer_callback_query(call.id, "Please set the exchange rate first!")
    else:
        user_id = call.message.chat.id
        type_fee = call.data.split("_")[-2]  # 'korea' or 'overseas'

        if not req_id:
            bot.send_message(user_id, "Request not found.")
            return

        if type_fee == "korea":
            currency = "₩"
        else:
            currency = "$"

        bot.send_message(user_id, f"Please enter the {type_fee.capitalize()} fee in {currency} for VIN: {vin} in numbers.")
        bot.register_next_step_handler(call.message, handle_fee_input, type_fee, req_id, vin, call)



def handle_fee_input(message, fee_type, req_id, vin, call):
    user_id = message.chat.id

    if not message.text.isdigit():
        bot.answer_callback_query(call.id, "Invalid input. Please enter a valid numeric amount.")
        return
    fee_amount = float(message.text)


    if fee_type == "korea":
        oot.update_orders(col_name="kfee", col_val=fee_amount, param="request_id", param_val=req_id)
        currency = "₩"
    else:
        oot.update_orders(col_name="overseasfee", col_val=fee_amount, param="request_id", param_val=req_id)
        currency = "$"
    if user_id in admin_ids:
        for admin in admin_ids:
            bot.send_message(admin, f"{fee_type.capitalize()} fee for VIN {vin} has been updated to {fee_amount:,}{currency}")
    else:
        for admin in admin_ids+user_id:
            bot.send_message(admin, f"{fee_type.capitalize()} fee for VIN {vin} has been updated to {fee_amount:,}{currency}")


    user_id = oot.get_request_by_column("vin", vin, "issuerID")[0]
    balance, not_used = oot.get_balance(user_id)
    if fee_type == "korea":
        after_fee_balance = balance - fee_amount

    else:
        rate = oot.get_orders_by_column("request_id", req_id, "rate")[0]
        rate_price = fee_amount * rate

        after_fee_balance = balance - rate_price

    oot.update_balance(after_fee_balance, user_id)



user_images = {}
message_sent_flags = {}


@bot.callback_query_handler(func=lambda call: call.data.startswith("upload_doc_"))
def upload_doc(call):
    vin = call.data.split("_")[-1]
    result = oot.get_request_by_column("vin", vin, "documents")

    if result[0] == 0:
        sent_msg = bot.send_message(call.message.chat.id, "Please upload document images...")
        user_last_message[call.message.chat.id] = sent_msg.message_id
        state_manager.user_state(call.message, f"awaiting_images_{vin}")
    else:
        bot.answer_callback_query(call.id, "You have already uploaded document images for this car.")


@bot.message_handler(content_types=["photo"],
                     func=lambda message: state_manager.get_state(message.from_user.id).startswith("awaiting_images_"))
def handle_uploaded_images(message):

    user_id = message.chat.id
    state = state_manager.get_state(user_id)
    vin = state.split("_")[-1]

    if user_id not in user_images:
        user_images[user_id] = {"images": [], "vin": vin}
        message_sent_flags[user_id] = False

    user_images[user_id]["images"].append(message.photo[-1].file_id)

    # Send confirmation only once per session
    if not message_sent_flags[user_id]:
        threading.Timer(2.0, send_upload_message, args=[user_id]).start()
        message_sent_flags[user_id] = True

    # Instead of waiting for 100 images, zip all when the user sends the "/done" command
    if len(user_images[user_id]["images"]) >= 1000:
        send_msg = bot.send_message(user_id, "Creating your ZIP file now...")
        zip_path = md.create_zip_and_save(user_images, user_id, vin)
        if zip_path:
            bot.send_document(user_id, open(zip_path, 'rb'))
            os.remove(zip_path)  # Cleanup
        message_sent_flags.pop(user_id, None)
        bot.delete_message(user_id, send_msg.message_id)


def send_upload_message(user_id):
    bot.send_message(user_id, "Your images have been uploaded. When you're done, send /done to create a ZIP file.")



@bot.message_handler(commands=["done"],
                     func=lambda message: state_manager.get_state(message.from_user.id).startswith("awaiting_images_"))
def handle_done_command(message):

    user_id = message.chat.id
    state = state_manager.get_state(user_id)
    vin = state.split("_")[-1]

    if user_id in user_images and len(user_images[user_id]["images"]) > 0:
        bot.send_message(user_id, "Zipping your images now...")
        zip_path = md.create_zip_and_save(user_images, user_id, vin)

        oot.update_request(col_name="documents", col_val=1, param_val=vin, param="vin")

        if zip_path:
            md.unzip_and_send_files(user_id, zip_path)

        message_sent_flags.pop(user_id, None)
    else:
        bot.send_message(user_id, "No images found. Please upload at least one image.")



@bot.callback_query_handler(func=lambda call: call.data.startswith("exchange_rate_"))
def exchange_rate(call):
    vin = call.data.split("_")[-1]

    user_id, last_price, req_id = oot.get_request_by_column("vin", vin, "issuerID", "last_price", "id")

    bot.send_message(call.message.chat.id, "Please enter the exchange rate:")
    bot.register_next_step_handler(call.message, lambda message: process_exchange_rate(message, req_id, user_id, last_price, vin))


def process_exchange_rate(message, req_id, user_id, price, vin):
    try:
        rate = float(message.text.strip())
        rate_price = float(price / rate)

        oot.update_orders(col_name="rate", col_val=rate, param="request_id", param_val=req_id)
        if user_id in admin_ids:
            for admin in admin_ids:
                bot.send_message(
                    admin,
                    f"From <b>{message.chat.first_name}</b>\n\n✅ Exchange rate set to: {rate:,} 💰\n\nfor VIN: `{vin}`\n\nPrice: {price} / {rate}= {rate_price:,.2f}"
                    , parse_mode="HTML"
                )
        else:
            for admin in admin_ids+user_id:
                bot.send_message(
                    admin,
                    f"From <b>{message.chat.first_name}</b>\n\n✅ Exchange rate set to: {rate:,} 💰\n\nfor VIN: `{vin}`\n\nPrice: {price} / {rate}= {rate_price:,.2f}"
                    , parse_mode="HTML"
                )

    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid input. Please enter a valid number.")
        bot.register_next_step_handler(message, process_exchange_rate, vin)


@bot.callback_query_handler(func=lambda call: call.data.startswith("order_completed_"))
def order_complete(call):
    vin = call.data.split("_")[-1]

    req_id, issuer_id = oot.get_request_by_column("vin", vin, "id", "issuerID")

    k_fee, overseas_fee = oot.get_orders_by_column("request_id", req_id, "kfee", "overseasfee")

    if k_fee is None or overseas_fee is None:
        bot.answer_callback_query(call.id, "Please enter both fees first!")
    else:
        status_order = oot.get_admin_by_column("requestID", req_id, "payment_status")[0]

        if status_order != "Paid":

            oot.update_orders(col_name='is_paid', col_val="Paid", param="request_id", param_val=req_id)
            oot.update_admin(col_name='payment_status', col_val="Paid", param="requestID", param_val=req_id)
            oot.update_admin(col_name='is_completed', col_val=1, param="requestID", param_val=req_id)

            for admin_id in admin_ids:
                msg_id = msg_ids.get(admin_id)
                bot.send_message(admin_id, f"Payment process completed by {call.message.chat.first_name}. Request for (VIN: {vin}) is now closed!")
                try:
                    bot.unpin_chat_message(admin_id, msg_id)
                except Exception as e:
                    if "message to delete not found" in str(e):
                        continue
                    else:
                        continue

        else:
            bot.answer_callback_query(call.id, f"Request for (VIN: {vin}) is already closed and confirmed!")


@bot.message_handler(commands=['all_orders'])
def handle_all_orders(message):
    state_manager.user_state(message, "all_orders")

    user_id = message.chat.id

    if user_id in admin_ids:
        columns, all_orders_data = oot.get_requests_ordered()
    else:
        columns, all_orders_data = oot.get_request_by_column_all("issuerID", user_id, "order_id", "model", "vin")

    if not all_orders_data:
        sent_msg = bot.send_message(user_id, "No orders found.")
        user_last_message[user_id] = sent_msg.message_id
        return


    pg_nav.send_page(user_id, page=1, data=all_orders_data, columns=columns, items_per_page=9, context="all_orders")


@bot.callback_query_handler(func=lambda call: call.data.startswith("all_orders_"))
def view_all_orders(call):
    order_id = call.data.split("_")[-1]

    columns, request_data = oot.all_orders_info(order_id)

    full_request_info, inline_keyboard = pg_nav.format_results(columns, request_data, "all_orders", call.message.chat.id)

    sent_msg = bot.send_message(
        chat_id=call.message.chat.id,
        text=f"<b>Request Info:</b>\n\n{full_request_info}",
        parse_mode="HTML",
        reply_markup=inline_keyboard
    )

    user_last_request_info[call.message.chat.id] = sent_msg.message_id


@bot.callback_query_handler(func=lambda call: call.data.startswith("documents_show_"))
def show_documents(call):
    vin = call.data.split("_")[-1]
    zip_filename = f"documents/{vin}_documents.zip"

    if not os.path.exists(zip_filename):
        bot.answer_callback_query(call.id, "No documents found for this VIN.")
        return

    bot.answer_callback_query(call.id, "Retrieving documents... Please wait.")
    md.unzip_and_send_files(call.message.chat.id, zip_filename)


@bot.callback_query_handler(func=lambda call: call.data.startswith("payment_show_"))
def retrieve_payment(call):
    vin = call.data.split("_")[-1]
    file_path = f"content/payment_images/{vin}_payment.jpg"

    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            bot.send_photo(call.message.chat.id, f)
            bot.send_message(call.message.chat.id, f"Receipt for VIN: {vin}.")
    else:
        bot.answer_callback_query(call.id, "❌ No receipt found for this VIN.")


@bot.message_handler(commands=['balance'])
def handle_balance(message):
    user_id = message.chat.id

    # Check if user is an admin
    if user_id in admin_ids:
        # Fetch all users' balances
        results = oot.get_balance()  # No user_id means fetch all

        if results:
            balances_text = ""
            for result in results:
                balance, issuer_id = result
                if balance is not None:  # Skip entries with None as balance
                    username = oot.get_request_by_column("issuerID", issuer_id, "username")[0]
                    balances_text += f"Username: {username}\nBalance: {balance:,}₩\n\n"

            if balances_text:
                bot.send_message(user_id, f"All Users' Balances:\n\n{balances_text}")
            else:
                bot.send_message(user_id, "No balances available for users.")
        else:
            bot.send_message(user_id, "No balances found.")

    else:
        # Fetch only the balance for this user
        result = oot.get_balance(user_id)
        if result:
            balance, user_id = result
            if balance is not None:
                username = oot.get_request_by_column("issuerID", user_id, "username")[0]
                bot.send_message(user_id, f"Username: {username}\nBalance: {balance:,}₩")
            else:
                bot.send_message(user_id, "Your balance is not set.")
        else:
            bot.send_message(user_id, "You don't have a balance record.")


user_edit_context = {}
@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_orders_"))
def handle_edit_order(call):
    parts = call.data.split('_')
    vin = parts[2]

    req_id = oot.get_request_by_column("vin", vin, "id")[0]

    editable_fields = [
        {'number': 1, 'display': 'Model name', 'column': 'model', 'table': 'requests', 'key_column': 'vin', 'key_value': vin, 'type': 'str'},
        {'number': 2, 'display': 'Plate number', 'column': 'platenumber', 'table': 'requests', 'key_column': 'vin', 'key_value': vin, 'type': 'str'},
        {'number': 3, 'display': 'VIN', 'column': 'vin', 'table': 'cars', 'key_column': 'requests', 'key_value': vin, 'type': 'str'},
        {'number': 4, 'display': 'Last price', 'column': 'last_price', 'table': 'requests', 'key_column': 'id', 'key_value': req_id, 'type': 'int'},
        {'number': 5, 'display': 'VAT', 'column': 'vat', 'table': 'requests', 'key_column': 'request_id', 'key_value': req_id, 'type': 'int'},
        {'number': 6, 'display': 'Paid price', 'column': 'paidprice', 'table': 'requests', 'key_column': 'request_id', 'key_value': req_id, 'type': 'int'},
        {'number': 7, 'display': 'Exchange rate', 'column': 'rate', 'table': 'orders', 'key_column': 'request_id', 'key_value': req_id, 'type': 'float'},
        {'number': 8, 'display': 'Fees in Korea', 'column': 'kfee', 'table': 'orders', 'key_column': 'request_id', 'key_value': req_id, 'type': 'int'},
        {'number': 9, 'display': 'Overseas fee', 'column': 'overseasfee', 'table': 'orders', 'key_column': 'request_id', 'key_value': req_id, 'type': 'int'},
        {'number': 10, 'display': 'Dealer phone number', 'column': 'phoneNumber', 'table': 'requests', 'key_column': 'id', 'key_value': req_id, 'type': 'int'}
    ]

    message_text = "Select the field to edit:\n"
    for field in editable_fields:
        message_text += f"{field['number']}. {field['display']}\n"
    message_text += "\nPress the corresponding number:"

    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []
    for field in editable_fields:
        buttons.append(InlineKeyboardButton(str(field['number']), callback_data=f"edit_field_{field['number']}_{req_id}"))
    buttons.append(InlineKeyboardButton("❌ Cancel", callback_data=f"edit_cancel_{req_id}"))
    keyboard.add(*buttons)

    sent_msg = bot.send_message(call.message.chat.id, message_text, reply_markup=keyboard)
    bot.answer_callback_query(call.id)

    user_last_message[call.message.chat.id] = sent_msg.message_id


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_field_"))
def handle_edit_field_selection(call):
    parts = call.data.split('_')
    field_number = int(parts[2])
    req_id = parts[-1]

    delete_last_message(call.message.chat.id)

    editable_fields = [
        {'number': 1, 'display': 'Model name', 'column': 'model', 'table': 'requests', 'key_column': 'id',
         'key_value': req_id, 'type': 'str'},
        {'number': 2, 'display': 'Plate number', 'column': 'plateNumber', 'table': 'requests', 'key_column': 'id',
         'key_value': req_id, 'type': 'str'},
        {'number': 3, 'display': 'VIN', 'column': 'vin', 'table': 'requests', 'key_column': 'id', 'key_value': req_id,
         'type': 'str'},
        {'number': 4, 'display': 'Last price', 'column': 'last_price', 'table': 'requests', 'key_column': 'id',
         'key_value': req_id, 'type': 'int'},
        {'number': 5, 'display': 'VAT', 'column': 'vat', 'table': 'requests', 'key_column': 'id',
         'key_value': req_id, 'type': 'int'},
        {'number': 6, 'display': 'Paid price', 'column': 'paidprice', 'table': 'requests', 'key_column': 'id ',
         'key_value': req_id, 'type': 'int'},
        {'number': 7, 'display': 'Exchange rate', 'column': 'rate', 'table': 'orders', 'key_column': 'request_id',
         'key_value': req_id, 'type': 'float'},
        {'number': 8, 'display': 'Fees in Korea', 'column': 'kfee', 'table': 'orders', 'key_column': 'request_id',
         'key_value': req_id, 'type': 'int'},
        {'number': 9, 'display': 'Overseas fee', 'column': 'overseasfee', 'table': 'orders', 'key_column': 'request_id',
         'key_value': req_id, 'type': 'int'},
        {'number': 10, 'display': 'Dealer phone number', 'column': 'phoneNumber', 'table': 'requests',
         'key_column': 'id', 'key_value': req_id, 'type': 'str'}
    ]

    selected_field = next((f for f in editable_fields if f['number'] == field_number), None)
    if not selected_field:
        bot.answer_callback_query(call.id, "Invalid field selected.")
        return

    user_edit_context[call.message.chat.id] = selected_field
    state_manager.user_state(call.message, f"awaiting_edit_{selected_field['column']}")

    sent_msg = bot.send_message(call.message.chat.id, f"Enter new value for {selected_field['display']}:")
    bot.answer_callback_query(call.id)

    user_last_message[call.message.chat.id] = sent_msg.message_id


@bot.message_handler(func=lambda message: state_manager.get_state(message.chat.id).startswith("awaiting_edit_"))
def handle_edit_value_input(message):
    user_id = message.chat.id

    bot.delete_message(user_id, message.message_id)
    delete_last_message(message.chat.id)

    if user_id not in user_edit_context:
        bot.send_message(user_id, "Edit session expired. Please start over.")
        state_manager.user_state(message, None)
        return

    selected_field = user_edit_context[user_id]
    new_value = message.text.strip()

    # Validate input based on type
    try:
        if selected_field['type'] == 'int':
            new_value = int(new_value)
        elif selected_field['type'] == 'float':
            new_value = float(new_value)
        # Add other types if needed
    except ValueError:
        bot.send_message(user_id, "Invalid format. Please enter a valid number.")
        return

    # Update database
    success = oot.update_table(
        selected_field['table'],
        selected_field['column'],
        new_value,
        selected_field['key_column'],
        selected_field['key_value']
    )

    if success:
        sent_msg = bot.send_message(user_id, f"✅ {selected_field['display']} updated successfully!")
        req_id = selected_field['key_value']
        order_id = oot.get_orders_by_column("request_id", req_id, "order_id")[0]
        trigger_view_all_orders(user_id, order_id)
    else:
        sent_msg = bot.send_message(user_id, "❌ Failed to update. Please try again.")

    user_last_message[message.chat.id] = sent_msg.message_id
    bot.delete_message(user_id, user_last_message[user_id])

    del user_edit_context[user_id]
    state_manager.user_state(message, "edit_orders_done")


def trigger_view_all_orders(user_id, req_id):
    if user_id in user_last_message:
        try:
            bot.delete_message(user_id, user_last_message[user_id])
        except Exception as e:
            print(f"Error deleting confirmation message: {e}")
        finally:
            del user_last_message[user_id]

    if user_id in user_last_request_info:
        try:
            bot.delete_message(user_id, user_last_request_info[user_id])
        except Exception as e:
            print(f"Error deleting previous order details message: {e}")
        finally:
            del user_last_request_info[user_id]

    class FakeCall:
        message = type("Message", (), {"chat": type("Chat", (), {"id": user_id})})
        data = f"all_orders_{req_id}"

    view_all_orders(FakeCall())


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_cancel_"))
def handle_edit_cancel(call):
    delete_last_message(call.message.chat.id)

    user_id = call.message.chat.id
    if user_id in user_edit_context:
        del user_edit_context[user_id]
    state_manager.user_state(call.message, None)
    sent_msg = bot.send_message(user_id, "Edit cancelled.")

    user_last_message[call.message.chat.id] = sent_msg.message_id

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("comment_"))
def comment_handler(call):
    req_id = call.data.split("_")[-1]
    count_comment = call.data.split("_")[-2]

    state_manager.user_state(call.message, f"commenting_{req_id}")

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    show_comments_button = InlineKeyboardButton(f"📝 Show comments - {count_comment}", callback_data=f"show_comments_{req_id}")
    comment_button = InlineKeyboardButton("✏️ Leave comment", callback_data=f"commenting_{req_id}")
    inline_keyboard.add(show_comments_button, comment_button)


    bot.send_message(call.message.chat.id, "Choose one option below:", reply_markup=inline_keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("commenting_"))
def commenting(call):
    req_id = call.data.split("_")[-1]

    bot.send_message(call.message.chat.id, "Leave your comment:")
    bot.register_next_step_handler(call.message, get_comment, req_id)


def get_comment(message, req_id):
    admin_id = message.chat.id
    username = message.chat.first_name

    vin = oot.get_request_by_column("id", req_id, "vin")[0]

    comment = message.text.strip()

    oot.insert_comments(req_id, admin_id, username, comment)

    for admin in admin_ids:
        bot.send_message(admin, f"<b>{username}</b> has commented on <b>{vin}</b>\n\n <b>{comment}</b>", parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith("show_comments_"))
def show_comments(call):
    req_id = call.data.split("_")[-1]

    vin = oot.get_request_by_column("id", req_id, "vin")[0]

    comments = oot.get_comments(req_id)

    if not comments:
        bot.answer_callback_query(call.id, "No comments found for this request.")
        return

    comment_text = "\n\n".join([f"👤 {username}: {comment}" for username, comment in comments])

    bot.send_message(call.message.chat.id, f"📝 Comments on <b>{vin}</b>:\n\n{comment_text}", parse_mode="HTML")



if __name__ == '__main__':
    bot.infinity_polling()
