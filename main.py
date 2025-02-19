from dotenv import load_dotenv
from datetime import datetime
import telebot \
    , sqlite3 \
    , logging \
    , os \
    , send_file_pic as sfp \
    , userState \
    , createQueries as cq \
    , tempTableManager as ttm \
    , operations_orders as oor \
    , page_navigation as pg_nav
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
cq.create_table()


###### STATE MANAGER ######
state_manager = userState.UserStateManager(db)


###### CLASS TEMP TABLE MANAGER ######
temp_manager = ttm.TempTableManager(db)


## pinned messages = []
msg_ids = {}


### Full access admin
def is_full_admin(user_id):
    return user_id in admin_ids


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

    user_id = call.message.chat.id

    ## get results from temp table
    car_info = temp_manager.get_temp_results(user_id)

    if car_info:
        model, vin, plate_number, last_price, vat = car_info
        username = call.message.chat.first_name

        # Insert the information into the actual `requests` table
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        connection = sqlite3.connect(db)
        with connection:
            connection.execute("""
                INSERT INTO requests (model, vin, platenumber, last_price, vat, issuerID, username, messageID, date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (model, vin, plate_number, last_price, vat, user_id, username, call.message.message_id-1, now_time))

        # Clear the temp table for the user after insertion
        temp_manager.clear_temp_request(user_id)

        # Send a confirmation message to the user
        bot.send_message(call.message.chat.id, "Your request has been successfully submitted. Thank you!")
        send_to_admins(username, user_id, model, vin, plate_number, last_price, vat)
        state_manager.user_state(call.message, "start_menu")
    else:
        bot.send_message(call.message.chat.id, "Error has occurred. Please try again right now. It might work or not.")


@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def handle_cancellation(call):
    user_id = call.from_user.id

    # Clear the temp table for the user (cancel the current process)
    temp_manager.clear_temp_request(user_id)

    bot.send_message(call.message.chat.id, "Your request has been canceled. No thank you!")

    # Optionally, move the user to a new state (e.g., back to main menu)
    state_manager.user_state(call.message, "start_menu")


def send_to_admins(username, last_modify_userID, model, vin, plate_number, last_price, vat):

    admin_summary_message = (
                f"Here is the information that has been entered by {username}:\n\n"
                f"Model: <b>{model}</b>\n"
                f"VIN: <b>{vin}</b>\n"
                f"Plate Number: <b>{plate_number}</b>\n"
                f"Last Price: <b>{last_price}</b>\n"
                f"VAT: <b>{vat}</b>\n\n"
                f"User ID: {last_modify_userID}\n"
    )

    inline_keyboard = InlineKeyboardMarkup(row_width=2)
    confirm_button = InlineKeyboardButton("Confirm ✅", callback_data="confirm_by_admin")
    cancel_button = InlineKeyboardButton("Cancel ❌", callback_data="cancel_by_admin")
    edit_button = InlineKeyboardButton("Edit 🖋️", callback_data="edit_by_admin")
    inline_keyboard.add(confirm_button, cancel_button)
    inline_keyboard.add(edit_button)

    for admin in admin_ids:
        sent_message = bot.send_message(admin, admin_summary_message, reply_markup=inline_keyboard, parse_mode="HTML")
        msg_ids[admin] = sent_message.message_id
        bot.pin_chat_message(admin, sent_message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == "confirm_by_admin")
def handle_confirmation_by_admin(call):

    message_text = call.message.text
    vin = None
    vin_num = [line for line in message_text.split('\n') if line.startswith("VIN:")]
    if vin_num:
        vin = vin_num[0].split("VIN: ")[1]

    req_id, issuer_id = oor.get_request_by_column("vin", vin, "id", "issuerID")

    result = oor.check_status(vin)

    if result[0] != 'Confirmed':
        admin_id = call.message.chat.id

        # Prepare a summary message
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        if req_id:
            oor.insert_order(req_id, 1, "Pending", admin_id, now_time)


        for admin in admin_ids + [issuer_id]:
            bot.send_message(admin, f"Request has been confirmed by {call.message.chat.first_name}, and it is ready for payment.")
        bot.send_message(admin_id, "You have confirmed that every data is correct and ready for payment. Thank you!")
        oor.update_request(col_name='status', col_val="Confirmed", param="vin", param_val=vin)

    else:
        bot.send_message(call.message.chat.id, "This request has been confirmed.")


@bot.callback_query_handler(func=lambda call: call.data == "cancel_by_admin")
def handle_cancel_by_admin(call):
    message_text = call.message.text

    vin = None
    vin_num = [line for line in message_text.split('\n') if line.startswith("VIN:")]
    if vin_num:
        vin = vin_num[0].split("VIN: ")[1]

    vin, username, issuer_id = oor.get_request_by_column("vin", vin, "vin", "username", "issuerID")

    oor.update_request(col_name='status', col_val="Cancelled", param="issuerID", param_val=issuer_id)

    msg = bot.send_message(
            call.message.chat.id,
            f"Request (VIN: {vin} by {username}) has been cancelled by {call.message.chat.first_name}, and it will be returned to *{username}*.\n\n"
            f"Explain the reason (mandatory): ", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda message: process_cancellation_reason(message,issuer_id, vin, username))


def process_cancellation_reason(msg, issuer_id, vin, username):
    cancellation_reason = msg.text

    message_req_id = oor.get_request_by_column("issuerID", issuer_id, "messageID")[0]

    bot.send_message(issuer_id, f"❌ Your request (VIN: {vin}) has been cancelled, and is deleted by now.\n\n📌 *Reason:* {cancellation_reason}",
        parse_mode="Markdown")

    for admin in admin_ids:
        bot.send_message(admin, f"The request (VIN: {vin} by {username}) has been sent back to *{username}*. The reason that has been entered:\n\n*{cancellation_reason}*", parse_mode="Markdown")

        msg_id = msg_ids.get(admin)
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

    oor.delete_request(issuer_id)

    bot.delete_message(issuer_id, message_req_id+1)


@bot.callback_query_handler(func=lambda call: call.data == "edit_by_admin")
def view_edit_requests_admin(call):
    state_manager.user_state(call.message, "view_edit_admin")

    message_text = call.message.text

    last_modify_userid = None
    user_id_line = [line for line in message_text.split('\n') if line.startswith("User ID:")]
    if user_id_line:
        last_modify_userid = user_id_line[0].split("User ID: ")[1]

    vin=None
    vin_num = [line for line in message_text.split('\n') if line.startswith("VIN:")]
    if vin_num:
        vin = vin_num[0].split("VIN: ")[1]

    columns, req_one_data = oor.get_requests_all(vin)

    full_req_one_info, inline_keyboard = pg_nav.format_results(columns, req_one_data, context="requests_edit")

    bot.send_message(
        chat_id=call.message.chat.id,
        text=f"Request Info:\n\n{full_req_one_info}",
        reply_markup=inline_keyboard,
        parse_mode='HTML'
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_request_"))
def edit_request_callback(call):
    state_manager.user_state(call.message, "edit_request_admin")

    edit_index = call.data.split("_")[-2]
    vin = call.data.split("_")[-1]

    bot.send_message(call.message.chat.id, f"Edit the {edit_index}:")
    bot.register_next_step_handler(call.message, lambda msg: edit_value_handler(msg, edit_index, vin))


def edit_value_handler(message, column, vin):

    oor.update_request(col_name=f'{column}', col_val=message.text, param="vin", param_val=vin)
    oor.update_request(col_name="status", col_val="Edited", param="vin", param_val=vin)

    for admin in admin_ids:
        bot.send_message(admin, f"VIN: {vin}. The {column} is now set to {message.text}.")


@bot.callback_query_handler(func=lambda call: call.data == "all_by_admin")
def handle_all_by_admin(call):
    state_manager.user_state(call.message, "on_all_by_admin")

    columns, req_data = oor.get_requests_all()
    pg_nav.send_page(call.message.chat.id, page=1, columns=columns, data=req_data, context="requests", items_per_page=9)

    bot.send_message(call.message.chat.id, "all by admin is on")


@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def handle_page_navigation(call):
    try:
        callback_data_parts = call.data.split("_")

        page = int(callback_data_parts[1])
        context = callback_data_parts[2]
        columns, rows = oor.get_requests_all()
        data = rows
        items_per_page = 9
        total_pages = (len(data) - 1) // items_per_page + 1
        if page < 1 or page > total_pages:
            logger.error(f"Page number out of bounds: {page} (total pages: {total_pages})")
            return

        pg_nav.send_page(call.message.chat.id, page=page, data=data, columns=columns, items_per_page=items_per_page,
                  message_id=call.message.message_id, context=context)
    except Exception as e:
        logger.error(f"Error handling page navigation: {e}")
        bot.answer_callback_query(call.id, text="There was an error. Please try again.")


if __name__ == '__main__':
    bot.infinity_polling()