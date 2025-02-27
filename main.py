import threading

from dotenv import load_dotenv
from datetime import datetime
import telebot \
    , sqlite3 \
    , logging \
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

    full_List = KeyboardButton("Full list")
    send_Request = KeyboardButton("Send request")
    keyboard.row(full_List, send_Request)
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
                sent_msg = bot.send_message(message.chat.id, "Don't play with me! You used this VIN number already! 🚫")
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
        vat_value = float(message.text.strip())
        temp_manager.update_temp_results(user_id, "vat", vat_value)

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

    car_info = temp_manager.get_temp_results(user_id)

    if car_info:
        model, vin, plate_number, last_price, vat, phone_number = car_info  # Assuming the tuple has these values
        summary_message = (
            f"Here is the information you entered:\n\n"
            f"Model: <b>{model}</b>\n"
            f"Plate Number: <b>{plate_number}</b>\n"
            f"VIN: <b>{vin}</b>\n"
            f"Last Price: <b>{last_price:,}₩</b>\n"
            f"VAT: <b>{vat:,}₩</b>\n"
            f"Dealer phone number: <b>{phone_number}</b>\n\n"
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
    sent_msg = bot.send_message(message.chat.id, summary_message, reply_markup=inline_keyboard, parse_mode="HTML")
    user_last_message[message.chat.id] = sent_msg.message_id
    bot.delete_message(message.chat.id, message.message_id)
    state_manager.user_state(message, "awaiting_confirmation")


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
            model, vin, plate_number, last_price, vat, phone_number = car_info
            username = call.message.chat.first_name

            now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            connection = sqlite3.connect(db)
            with connection:
                connection.execute("""
                    INSERT INTO requests (model, vin, platenumber, last_price, vat, issuerID, username, messageID, date, phoneNumber, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (model, vin, plate_number, last_price, vat, user_id, username, call.message.message_id, now_time, phone_number, "Confirmed"))
            connection.close()

            # Clear the temp table for the user after insertion
            temp_manager.clear_temp_request(user_id)

            # Send a confirmation message to the user

            sent_msg = bot.send_message(call.message.chat.id, "Your request has been successfully submitted. Thank you!")

            user_last_message[call.message.chat.id] = sent_msg.message_id

            req_id = oot.get_request_by_column("vin", vin, "id")[0]

            send_to_admins(username, model, vin, plate_number, last_price, vat, phone_number, req_id)
            state_manager.user_state(call.message, "start_menu")
        else:
            bot.send_message(call.message.chat.id, "Error has occurred. Please try again right now. It might work or not.")


@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def handle_cancellation(call):
    user_id = call.from_user.id

    # Clear the temp table for the user (cancel the current process)
    temp_manager.clear_temp_request(user_id)

    bot.delete_message(call.message.chat.id, call.message.message_id)

    sent_msg = bot.send_message(call.message.chat.id, "Your request has been canceled. No thank you!")
    user_last_message[call.message.chat.id] = sent_msg.message_id

    # Optionally, move the user to a new state (e.g., back to main menu)
    state_manager.user_state(call.message, "start_menu")


def send_to_admins(username, model, vin, plate_number, last_price, vat, phone_number, req_id):

    admin_summary_message = (
                f"Here is the information that has been entered by {username}:\n\n"
                f"Model: <b>{model}</b>\n"
                f"Plate Number: <b>{plate_number}</b>\n"
                f"VIN: <b>{vin}</b>\n"
                f"Last Price: <b>{last_price:,}₩</b>\n"
                f"VAT: <b>{vat:,}₩</b>\n"
                f"Dealer phone number: <b>{phone_number}</b>\n\n"
                f"Request ID: {req_id}\n"
    )

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    confirm_button = InlineKeyboardButton("Confirm ✅", callback_data="confirm_by_admin")
    cancel_button = InlineKeyboardButton("Cancel ❌", callback_data=f"cancel_by_admin|{vin}")
    edit_button = InlineKeyboardButton("Edit 🖋️", callback_data="edit_by_admin")
    inline_keyboard.add(confirm_button, cancel_button)
    inline_keyboard.add(edit_button)

    for admin in admin_ids:
        sent_message = bot.send_message(admin, admin_summary_message, reply_markup=inline_keyboard, parse_mode="HTML")
        msg_ids[admin] = sent_message.message_id
        bot.pin_chat_message(admin, sent_message.message_id)


def confirm_request(call, vin, req_id, issuer_id):
    result_admin = oot.get_admin_by_column("requestID", req_id, "status_req")

    # Update or insert admin confirmation
    admin_id = call.message.chat.id
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    if result_admin:
        oot.update_admin(col_name="status_req", col_val="Confirmed", param="requestID", param_val=req_id)
    else:
        msg_id = msg_ids.get(admin_id)
        oot.insert_order(req_id, 1, "Pending", admin_id, now_time)
        oot.insert_admin(admin_id, req_id, "Confirmed", "Pending", msg_id, now_time)

    # Send confirmation message
    confirmed_message = f"Request (VIN: {vin}) has been confirmed by {call.message.chat.first_name}, and it is ready for payment."

    recipients = admin_ids if issuer_id in admin_ids else admin_ids + [issuer_id]
    for recipient in recipients:
        bot.send_message(recipient, text=confirmed_message)

    # Send payment button
    inline_keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Payment 💳️", callback_data=f"payment_user_{vin}")
    )
    bot.send_message(issuer_id,
                     text=f"This request (VIN: {vin}) has been confirmed, and ready for payment. 💳 Payment status:\n⏳ PENDING...",
                     reply_markup=inline_keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "confirm_by_admin")
def handle_confirmation_by_admin(call):
    state_manager.user_state(call.message, "confirm_by_admin")
    message_text = call.message.text

    vin = None
    vin_num = [line for line in message_text.split('\n') if line.startswith("VIN:")]
    if vin_num:
        vin = vin_num[0].split("VIN: ")[1]

    if not vin:
        bot.send_message(call.message.chat.id, "❌ VIN not found in the message.")
        return

    query_result = oot.get_request_by_column("vin", vin, "issuerID", "id")

    if not query_result:
        bot.send_message(call.message.chat.id, f"❌ No request found for VIN: {vin}.")
        return

    issuer_id, req_id = query_result

    result_admin = oot.get_admin_by_column("requestID", req_id, "status_req")

    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    admin_id = call.message.chat.id

    if result_admin:
        status = result_admin[0]
        if status in ["Confirmed", "Cancelled"]:
            bot.send_message(call.message.chat.id, "This request has been confirmed or cancelled.")
        else:
            confirm_request(call, vin, req_id, issuer_id)
            oot.update_admin(col_name="status_req", col_val="Confirmed", param="requestID", param_val=req_id)
            oot.insert_order(req_id, 1, "Pending", admin_id, now_time)
    else:
        msg_id = msg_ids.get(admin_id)

        if req_id:
            oot.insert_order(req_id, 1, "Pending", admin_id, now_time)
            oot.insert_admin(call.message.chat.id, req_id, "Confirmed", "Pending", msg_id, now_time)
            confirm_request(call, vin, req_id, issuer_id)



@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_by_admin"))
def handle_cancel_by_admin(call):
    message_text = call.message.text

    callback_data_parts = call.data.split("|")
    vin = callback_data_parts[1] if len(callback_data_parts) > 1 else "Unknown"

    req_id = None
    req_id_num = [line for line in message_text.split('\n') if line.startswith("Request ID:")]
    if req_id_num:
        req_id = req_id_num[0].split("Request ID: ")[1]

    result = oot.get_admin_by_column("requestID", req_id, "status_req")

    if result:
        if result[0] == "Confirmed" or result[0] == "Cancelled":
            bot.send_message(call.message.chat.id, "This request has been confirmed or cancelled.")
        else:
            oot.update_admin(col_name="status_req", col_val="Cancelled", param="vin", param_val=vin)
    else:
        username, issuer_id = oot.get_request_by_column("id", req_id, "username", "issuerID")

        now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        oot.insert_admin(call.message.chat.id, req_id, "Cancelled", "Pending", call.message.chat.id, now_time)

        msg = bot.send_message(
                call.message.chat.id,
                f"Request (VIN: {vin} by {username}) has been cancelled by {call.message.chat.first_name}, and it will be returned to *{username}*.\n\n"
                f"Explain the reason (mandatory): ", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda message: process_cancellation_reason(message,issuer_id, vin, username))


def process_cancellation_reason(msg, issuer_id, vin, username):
    cancellation_reason = msg.text

    message_req_id = oot.get_request_by_column("issuerID", issuer_id, "messageID")[0]
    req_id = oot.get_request_by_column("issuerID", issuer_id, "id")[0]

    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    oot.insert_admin(msg.chat.id, req_id, "Cancelled", "Cancelled", message_req_id, now_time)

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

    full_req_one_info, inline_keyboard = pg_nav.format_results(columns, req_one_data, context="requests_edit")

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
            bot.send_message(call.message.chat.id, "This request has been confirmed or cancelled.")
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
    bot.register_next_step_handler(call.message, lambda msg: edit_value_handler(msg, edit_index, req_id))


def edit_value_handler(message, column, req_id):
    admin_id = message.chat.id
    msg_id = msg_ids.get(admin_id)

    if msg_id is None:
        bot.send_message(message.chat.id, "❌ Error: Cannot edit message. Message ID not found.")
        return

    # Validate VIN if editing VIN
    if column == "vin":
        if not is_valid_vin(message.text):
            bot.send_message(message.chat.id, "❌ Invalid VIN! It must be exactly 17 characters long and contain only uppercase letters and numbers.")
            return

    # Validate price if editing price-related fields
    if column in ["last_price", "vat"]:
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ Invalid input! Please enter a valid number for the price.")
            return

    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    result = oot.get_admin_by_column("requestID", req_id, "status_req")

    if result:
        oot.update_admin(col_name='status_req', col_val="Edited", param="requestID", param_val=req_id)
    else:
        oot.insert_admin(admin_id, req_id, "Edited", "Pending", msg_id, now_time)

    oot.update_request(col_name=f'{column}', col_val=message.text, param="id", param_val=req_id)
    message_id = oot.get_admin_by_column("requestID", req_id, "messageID")

    username, model, vin, plate_number, last_price, vat, phone_number = (
        oot.get_request_by_column("id", req_id, "username", "model", "vin", "plateNumber", "last_price", "vat", "phoneNumber"))

    try:
        send_to_admins(username, model, vin, plate_number, last_price, vat, phone_number, req_id)
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
    vin = call.data.split("_")[-1]

    bot.send_message(call.message.chat.id, "Please send a picture of the payment.")
    bot.register_next_step_handler(call.message, lambda msg: ask_for_price(msg, vin))


def ask_for_price(message, vin):
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
        bot.send_message(message.chat.id, "❌ Please send a valid picture.")
        bot.register_next_step_handler(message, ask_for_price, vin)


def send_price(message, picture, vin):
    try:
        price = float(message.text)

        oot.update_request(col_name="paidprice", col_val=price, param="vin", param_val=vin)

        user_id, last_price = oot.get_request_by_column("vin", vin, "issuerID", "last_price")

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
                     f"Price: {price:,}₩\n",
                reply_markup=inline_keyboard
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
        bot.send_message(call.message.chat.id, "Please set the exchange rate first!")
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
        bot.register_next_step_handler(call.message, handle_fee_input, type_fee, req_id, vin)



def handle_fee_input(message, fee_type, req_id, vin):
    user_id = message.chat.id

    if not message.text.isdigit():
        bot.send_message(user_id, "Invalid input. Please enter a valid numeric amount.")
        return
    fee_amount = float(message.text)


    currency = ""
    if fee_type == "korea":
        oot.update_orders(col_name="kfee", col_val=fee_amount, param="request_id", param_val=req_id)
        currency = "₩"
    else:
        oot.update_orders(col_name="overseasfee", col_val=fee_amount, param="request_id", param_val=req_id)
        currency = "$"
    # Notify admins about the fee update
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
        bot.send_message(call.message.chat.id, "You have already uploaded document images for this car.")


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
        bot.send_message(user_id, "Creating your ZIP file now...")
        zip_path = md.create_zip_and_save(user_images, user_id, vin)
        if zip_path:
            bot.send_document(user_id, open(zip_path, 'rb'))
            os.remove(zip_path)  # Cleanup
        message_sent_flags.pop(user_id, None)


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

    req_id, issuerID = oot.get_request_by_column("vin", vin, "id", "issuerID")

    status_order, adminID, messageID = oot.get_admin_by_column("requestID", req_id, "payment_status", "adminID", "messageID")

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
        bot.send_message(call.message.chat.id, f"Request for (VIN: {vin}) is already closed and confirmed!")



@bot.message_handler(commands=['all_orders'])
def handle_all_orders(message):
    state_manager.user_state(message, "all_orders")

    user_id = message.chat.id
    if user_id in admin_ids:
        columns, all_orders_data = oot.get_requests_all()
    else:
        columns, all_orders_data = oot.get_request_by_column_all("issuerID", user_id, "id", "model", "vin")
    pg_nav.send_page(message.chat.id, page=1, data=all_orders_data, columns=columns, items_per_page=9, context="all_orders")


@bot.callback_query_handler(func=lambda call: call.data.startswith("all_orders_"))
def view_all_orders(call):
    req_id = call.data.split("_")[-1]

    columns, request_data = oot.all_orders_info(req_id)

    full_request_info, inline_keyboard = pg_nav.format_results(columns, request_data, "all_orders")

    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"<b>Request Info:</b>\n\n{full_request_info}",
        parse_mode="HTML",
        reply_markup=inline_keyboard
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("documents_show_"))
def show_documents(call):
    vin = call.data.split("_")[-1]
    zip_filename = f"documents/{vin}_documents.zip"

    if not os.path.exists(zip_filename):
        bot.send_message(call.message.chat.id, "No documents found for this VIN.")
        return

    bot.send_message(call.message.chat.id, "Retrieving documents... Please wait.")
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
        bot.send_message(call.message.chat.id, "❌ No receipt found for this VIN.")


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


if __name__ == '__main__':
    bot.infinity_polling()
