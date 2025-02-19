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
    , operations_on_tables as oot \
    , page_navigation as pg_nav \
    , re
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


def is_valid_vin(vin):
    vin_pattern = r"^[A-Z0-9]{17}$"
    return re.fullmatch(vin_pattern, vin) is not None

@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_vin")
def enter_vin(message):
    user_id = message.from_user.id

    try:
        vin = message.text.strip()
        if not is_valid_vin(vin):
            bot.send_message(message.chat.id,
                             "Invalid VIN. Enter valid VIN 🚫")
            state_manager.user_state(message, "enter_vin")
        else:
            if temp_manager.vin_exists(vin):
                bot.send_message(message.chat.id, "Don't play with me mthrf**r! You used this VIN number already! 🚫")
                state_manager.user_state(message, "enter_vin")
            else:
                temp_manager.update_temp_results(user_id, "vin", vin)
                bot.send_message(message.chat.id, "Enter dealer phone number:")
                state_manager.user_state(message, "enter_dealer")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ An error occurred: {str(e)}")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_dealer")
def enter_dealer_phone(message):
    user_id = message.from_user.id

    ## update on temp table
    temp_manager.update_temp_results(user_id, "phoneNumber", message.text.strip())

    bot.send_message(message.chat.id, "Enter bank account number:")
    state_manager.user_state(message, "enter_bank")


@bot.message_handler(func=lambda message: state_manager.get_state(message.from_user.id) == "enter_bank")
def enter_bank_account(message):
    user_id = message.from_user.id

    ## update on temp table
    temp_manager.update_temp_results(user_id, "bankNumber", message.text.strip())

    bot.send_message(message.chat.id, "Enter plate number:")
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

        # model, vin, plate_number, last_price, vat, phoneNumber, bankNumber

        # Prepare a summary message
        if car_info:
            model, vin, plate_number, last_price, vat, phone_number, bank_account = car_info  # Assuming the tuple has these values
            summary_message = (
                f"Here is the information you entered:\n\n"
                f"Model: <b>{model}</b>\n"
                f"Dealer phone number: <b>{phone_number}</b>\n"
                f"Bank account number: <b>{bank_account}</b>\n"
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
        model, vin, plate_number, last_price, vat, phone_number, bank_number = car_info
        username = call.message.chat.first_name

        # Insert the information into the actual `requests` table
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        connection = sqlite3.connect(db)
        with connection:
            connection.execute("""
                INSERT INTO requests (model, vin, platenumber, last_price, vat, issuerID, username, messageID, date, phoneNumber, bankNumber)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (model, vin, plate_number, last_price, vat, user_id, username, call.message.message_id-1, now_time, phone_number, bank_number))
        connection.close()

        # Clear the temp table for the user after insertion
        temp_manager.clear_temp_request(user_id)

        # Send a confirmation message to the user
        bot.send_message(call.message.chat.id, "Your request has been successfully submitted. Thank you!")
        send_to_admins(username, user_id, model, vin, plate_number, last_price, vat, phone_number, bank_number)
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


def send_to_admins(username, issuer_id, model, vin, plate_number, last_price, vat, phone_number, bank_number):

    admin_summary_message = (
                f"Here is the information that has been entered by {username}:\n\n"
                f"Model: <b>{model}</b>\n"
                f"Dealer phone number: <b>{phone_number}</b>\n"
                f"Bank account number: <b>{bank_number}</b>\n"
                f"VIN: <b>{vin}</b>\n"
                f"Plate Number: <b>{plate_number}</b>\n"
                f"Last Price: <b>{last_price}</b>\n"
                f"VAT: <b>{vat}</b>\n\n"
                f"User ID: {issuer_id}\n"
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
    state_manager.user_state(call.message, "confirm_by_admin")
    message_text = call.message.text
    vin = None
    vin_num = [line for line in message_text.split('\n') if line.startswith("VIN:")]
    if vin_num:
        vin = vin_num[0].split("VIN: ")[1]

    req_id, issuer_id = oot.get_request_by_column("vin", vin, "id", "issuerID")

    result = oot.check_status(vin)

    if result[0] != 'Confirmed':
        admin_id = call.message.chat.id

        msg_id = msg_ids.get(admin_id)

        # Prepare a summary message
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        if req_id:
            oot.insert_order(req_id, 1, "Pending", admin_id, now_time)
            oot.insert_admin(call.message.chat.id, req_id, "Confirmed", "Pending", msg_id, now_time)

        confirmed_message = f"Request (VIN: {vin}) has been confirmed by {call.message.chat.first_name}, and it is ready for payment."

        if issuer_id in admin_ids:
            for admin in admin_ids:
                bot.send_message(admin, text=confirmed_message)
        else:
            for admin in admin_ids + [issuer_id]:
                bot.send_message(admin, text=confirmed_message)

        inline_keyboard = InlineKeyboardMarkup()
        payment_button = InlineKeyboardButton("Payment 💳️", callback_data=f"payment_user_{vin}")
        inline_keyboard.add(payment_button)

        bot.send_message(issuer_id, text=f"This request (VIN: {vin}) has been confirmed, and ready for payment. 💳 Payment status:\n⏳ PENDING...", reply_markup=inline_keyboard)
        oot.update_request(col_name='status', col_val="Confirmed", param="vin", param_val=vin)

    else:
        bot.send_message(call.message.chat.id, "This request has been confirmed.")


@bot.callback_query_handler(func=lambda call: call.data == "cancel_by_admin")
def handle_cancel_by_admin(call):
    message_text = call.message.text

    vin = None
    vin_num = [line for line in message_text.split('\n') if line.startswith("VIN:")]
    if vin_num:
        vin = vin_num[0].split("VIN: ")[1]

    result = oot.get_request_by_column("vin", vin, "vin", "username", "issuerID")

    vin_check = oot.check_status(vin)

    if vin_check[0] != 'Confirmed':
        username, issuer_id = None, None

        if result:
            vin, username, issuer_id = result
        else:
            bot.send_message(call.message.chat.id, "No request found")

        oot.update_request(col_name='status', col_val="Cancelled", param="issuerID", param_val=issuer_id)

        msg = bot.send_message(
                call.message.chat.id,
                f"Request (VIN: {vin} by {username}) has been cancelled by {call.message.chat.first_name}, and it will be returned to *{username}*.\n\n"
                f"Explain the reason (mandatory): ", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda message: process_cancellation_reason(message,issuer_id, vin, username))
    else:
        bot.send_message(call.message.chat.id, "This request has already been confirmed.")



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

    oot.delete_request(issuer_id)

    try:
        bot.delete_message(issuer_id, message_req_id+1)
    except Exception as e:
        if "message to delete not found" in str(e):
            pass
        else:
            pass


@bot.callback_query_handler(func=lambda call: call.data == "edit_by_admin")
def view_edit_requests_admin(call):
    state_manager.user_state(call.message, "view_edit_admin")

    message_text = call.message.text

    vin=None
    vin_num = [line for line in message_text.split('\n') if line.startswith("VIN:")]
    if vin_num:
        vin = vin_num[0].split("VIN: ")[1]

    columns, req_one_data = oot.get_requests_all(vin)

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

    oot.update_request(col_name=f'{column}', col_val=message.text, param="id", param_val=req_id)
    oot.update_request(col_name="status", col_val="Edited", param="id", param_val=req_id)

    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    oot.insert_admin(admin_id, req_id, "Edited", "Pending", msg_id, now_time)
    message_id = oot.get_admin_by_column("requestID", req_id, "messageID")

    username, issuer_id, model, vin, plate_number, last_price, vat, phone_number, bank_number = (
        oot.get_request_by_column("id", req_id, "username", "issuerID", "model", "vin", "plateNumber", "last_price", "vat", "phoneNumber", "bankNumber"))

    try:
        send_to_admins(username, issuer_id, model, vin, plate_number, last_price, vat, phone_number, bank_number)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error editing message: {e}")

    for i in range(message_id[0], message.message_id + 1):
        try:
            bot.delete_message(admin_id, i)
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
        bot.send_message(message.chat.id, "Now, please send the price.")
        bot.register_next_step_handler(message, send_price, picture, vin)
    else:
        bot.send_message(message.chat.id, "❌ Please send a valid picture.")
        bot.register_next_step_handler(message, ask_for_price)


def send_price(message, picture, vin):
    try:
        price = float(message.text)

        oot.update_request(col_name="vin", col_val=vin, param="last_price", param_val=int(price))

        inline_keyboard = InlineKeyboardMarkup()
        exchange_rate_button = InlineKeyboardButton("Exchange rate 💰", callback_data=f"exchange_rate_{vin}")
        payment_button = InlineKeyboardButton("Order completed ✅", callback_data=f"order_completed_{vin}")
        inline_keyboard.add(exchange_rate_button)
        inline_keyboard.add(payment_button)

        username = oot.get_request_by_column("vin", vin, "username")[0]

        for admin_id in admin_ids:
            bot.send_photo(admin_id, picture)
            bot.send_message(
                admin_id,
                text=f"User ({username}) has confirmed the payment request for (VIN: {vin}). 💳\n\n"
                     f"Price: {price}\n",
                reply_markup=inline_keyboard
            )

        bot.send_message(message.chat.id, f"Your payment details for (VIN: {vin}) have been sent to the admin 💼. Wait for order complete in the meantime!")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Please enter a valid price. Please send the price again.")
        bot.register_next_step_handler(message, send_price, picture)


@bot.callback_query_handler(func=lambda call: call.data.startswith("exchange_rate_"))
def exchange_rate(call):
    vin = call.data.split("_")[-1]

    user_id, last_price = oot.get_request_by_column("vin", vin, "issuerID", "last_price")

    bot.send_message(call.message.chat.id, "Please enter the exchange rate:")
    bot.register_next_step_handler(call.message, process_exchange_rate, vin, user_id, last_price)


def process_exchange_rate(message, vin, user_id, price):
    try:
        rate = float(message.text.strip())
        rate_price = float(price / rate)

        oot.update_orders(col_name="vin", col_val=vin, param="rate", param_val=int(rate))

        bot.send_message(
            user_id,
            f"From <b>{message.chat.first_name}</b>\n\n✅ Exchange rate for VIN {vin} is set to: {rate} 💰\n\nfor VIN: `{vin}`\n\nPrice: {price} / {rate}= {rate_price:.2f}"
            , parse_mode="HTML"
        )

        for admin in admin_ids:
            bot.send_message(
                admin,
                f"From <b>{message.chat.first_name}</b>\n\n✅ Exchange rate for VIN {vin} is set to: {rate} 💰\n\nfor VIN: `{vin}`\n\nPrice: {price} / {rate}= {rate_price:.2f}\n"
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
            bot.send_message(admin_id, f"Payment process completed by {call.message.chat.first_name}. Request for (VIN: {vin}) is now closed!")
            try:
                bot.unpin_chat_message(admin_id, messageID)
            except Exception as e:
                if "message to delete not found" in str(e):
                    continue
                else:
                    continue

    else:
        bot.send_message(call.message.chat.id, f"Request for (VIN: {vin}) is already closed and confirmed!")






@bot.message_handler(commands=['all_orders'])
def handle_all_by_admin(call):
    state_manager.user_state(call.message, "all_orders")

    columns, req_data = oot.get_requests_all()
    pg_nav.send_page(call.message.chat.id, page=1, columns=columns, data=req_data, context="requests", items_per_page=9)

    bot.send_message(call.message.chat.id, "all orders for admin is on")


@bot.callback_query_handler(func=lambda call: call.data.startswith("page_"))
def handle_page_navigation(call):
    try:
        callback_data_parts = call.data.split("_")

        page = int(callback_data_parts[1])
        context = callback_data_parts[2]
        columns, rows = oot.get_requests_all()
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