import telebot, logging, os
from dotenv import load_dotenv
import operations_on_tables as oot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


load_dotenv()
bot_token = os.getenv("BOT_TOKEN")
admin_ids_str  = os.getenv("ADMIN_IDS")
admin_ids = [int(ID.strip()) for ID in admin_ids_str.split(',')]

logger = logging.getLogger(__name__)
bot = telebot.TeleBot(bot_token)

def handle_page_navigation(call):
    try:
        callback_data_parts = call.data.split("_")

        page = int(callback_data_parts[1])
        context = callback_data_parts[2]

        if context == 'all_orders':
            if call.message.chat.id in admin_ids:
                columns, rows = oot.get_requests_ordered()
                data = rows
                items_per_page = 9
            else:
                columns, rows = oot.get_request_by_column_all("issuerID", call.message.chat.id, "order_id", "model", "vin")
                data = rows
                items_per_page = 9
        else:
            logger.error(f"Unknown context: {context}")
            return

        total_pages = (len(data) - 1) // items_per_page + 1
        if page < 1 or page > total_pages:
            logger.error(f"Page number out of bounds: {page} (total pages: {total_pages})")
            return

        send_page(call.message.chat.id, page=page, data=data, columns=columns, items_per_page=items_per_page, message_id=call.message.message_id, context=context)

    except Exception as e:
        logger.error(f"Error handling page navigation: {e}")
        bot.answer_callback_query(call.id, text="There was an error. Please try again.")


def send_page(chat_id, page, data, columns, items_per_page, context, message_id=None):
    start = (page - 1) * items_per_page
    end = start + items_per_page
    page_data = data[start:end]

    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = [
        InlineKeyboardButton(
            text=str(item[0]),
            callback_data=f"{context}_{item[0]}"
        ) for item in page_data
    ]
    for i in range(0, len(buttons), 3):
        keyboard.add(*buttons[i:i + 3])

    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page - 1}_{context}"))
    if end < len(data):
        navigation_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page + 1}_{context}"))
    if navigation_buttons:
        keyboard.add(*navigation_buttons)

    result_message = format_data(columns=columns, rows=page_data, context=context)

    if message_id:
        try:
            sent_msg = bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"Page {page} of {((len(data) - 1) // items_per_page) + 1}\n\n{result_message}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return sent_msg
        except telebot.apihelper.ApiTelegramException:
            sent_msg = bot.send_message(
                chat_id,
                text=f"Page {page} of {((len(data) - 1) // items_per_page) + 1}\n\n{result_message}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return sent_msg
    else:
        sent_msg = bot.send_message(
            chat_id,
            text=f"Page {page} of {((len(data) - 1) // items_per_page) + 1}\n\n{result_message}",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return sent_msg


def format_data(columns, rows, context):
    result_message = ""

    for row in rows:
        formatted_row = ""
        req_model = ""
        order_id = None
        req_vin = ""

        for col_name, value in zip(columns, row):
            if col_name.lower() == "order_id":
                order_id = value
            elif col_name.lower() == "model":
                req_model = value
            elif col_name.lower() == "vin":
                req_vin = value
        formatted_row += f"<b>{order_id}</b>. {req_model} --- <b>({req_vin})</b>\n"
        result_message += formatted_row
    return result_message


def format_results(columns, rows, context, user_id):
    result_message = ""
    inline_keyboard = InlineKeyboardMarkup(row_width=3)
    key_count = 0
    data_dict = {}
    editable_keys = []

    if context == "all_orders":
        for row in rows:
            model_name = plate_number = vin = dealer_number = paid = share = req_id = None
            doc = vat = price = username = date = kfee = rate = overseasfee = vat_share = None
            for col_name, value in zip(columns, row):
                if col_name.lower() == "model":
                    model_name = value
                elif col_name.lower() == "vin":
                    vin = value
                elif col_name.lower() == "platenumber":
                    plate_number = value
                elif col_name.lower() == "last_price":
                    price = value
                elif col_name.lower() == "vat":
                    vat = value
                elif col_name.lower() == "phonenumber":
                    dealer_number = value
                elif col_name.lower() == "paidprice":
                    paid = value
                elif col_name.lower() == "documents":
                    value = "Yes" if value else "No"
                    doc = value
                elif col_name.lower() == "date":
                    date = value
                elif col_name.lower() == "username":
                    username = value
                elif col_name.lower() == "rate":
                    rate = value
                elif col_name.lower() == "kfee":
                    kfee = value
                elif col_name.lower() == "overseasfee":
                    overseasfee = value
                elif col_name.lower() == "vat_percentage":
                    vat_share = value
                elif col_name.lower() == "percentage":
                    share = value
                elif col_name.lower() == "id":
                    req_id = value

            count_comments = len(oot.get_comments(req_id))

            result_message += f"Model name: \t<b>{model_name}</b>\n"
            result_message += f"Plate number: \t<b>{plate_number}</b>\n"
            result_message += f"VIN: \t<b>{vin}</b>\n"
            result_message += f"Last price: \t<b>{price:,}₩</b>\n"
            result_message += f"VAT: \t<b>{vat:,}₩</b>\n"
            result_message += f"Dealer phone number: \t<b>{dealer_number}</b>\n"
            result_message += f"Paid price:\t<b>{paid:,}₩</b>\n"
            result_message += f"Documents: \t<b>{doc}</b>\n"
            result_message += f"Exchange rate: \t<b>{rate:,}</b>\n"
            result_message += f"Fees in Korea: \t<b>{kfee:,}₩</b>\n"
            result_message += f"Overseas fee: \t<b>{overseasfee:,}$</b>\n"
            result_message += f"VAT share % (user): \t<b>{share}%</b>\n"
            result_message += f"VAT share amount (user): \t<b>{vat_share:,}₩</b>\n\n"
            result_message += f"Request created on \t<b>{date}</b> by <b>{username}</b>"

            inline_keyboard = InlineKeyboardMarkup(row_width=2)
            doc_show = InlineKeyboardButton("📄 Documents", callback_data=f"documents_show_{vin}")
            if doc == "Yes":
                inline_keyboard.add(doc_show)
            payment_show = InlineKeyboardButton("🧾 Payment receipt", callback_data=f"payment_show_{vin}")
            if paid is not None:
                inline_keyboard.add(payment_show)
            if user_id in admin_ids:
                edit_button = InlineKeyboardButton("🖋 Edit", callback_data=f"edit_orders_{vin}")
                comment_button = InlineKeyboardButton(f"💬 Comment - {count_comments}", callback_data=f"comment_{count_comments}_{req_id}")
                inline_keyboard.add(comment_button, edit_button)

            return result_message, inline_keyboard

    else:
        for index, row in enumerate(rows, start=1):
            data_dict = dict(zip(columns, row))

            editable_keys = [key for key in data_dict.keys() if key.lower() not in
                             ['username', 'id', 'issuerid', 'status', 'date', 'messageid', 'paidprice', 'documents', 'paid_type', 'percentage', 'vat_percentage']]
            key_count = len(editable_keys)

            result_message += f"<b>{index}.</b> Model: <b>{data_dict['model']}</b>\n"
            result_message += f"<b>{index+1}.</b> VIN: <b>{data_dict['vin']}</b>\n"
            result_message += f"<b>{index+2}.</b> Plate Number: <b>{data_dict['plateNumber']}</b>\n"
            result_message += f"<b>{index+3}.</b> Price: <b>{data_dict['last_price']:,}₩</b>\n"
            result_message += f"<b>{index+4}.</b> VAT: <b>{data_dict['vat']:,}₩</b>\n"
            result_message += f"<b>{index+5}.</b> Dealer phone number: <b>{data_dict['phoneNumber']}</b>\n\n"
            result_message += f"Requested by: <b>{data_dict['username']}</b>\n\n"

        buttons = [
            InlineKeyboardButton(f"{index + 1}", callback_data=f"edit_request_{editable_keys[index]}_{data_dict['id']}")
            for index in range(key_count)
        ]

        inline_keyboard.add(*buttons)


        return result_message, inline_keyboard

# if context == "teams":
        #     for col_name, value in zip(columns, row):
        #         if col_name.lower() == "teamname":
        #             team_name = value
        #         elif col_name.lower() == "teamid":
        #             team_id = value
        #     formatted_row += f"<b>{team_id}. {team_name}</b>\n"



# @bot.message_handler(func=lambda message: message.text == "F1 Drivers")
# def list_drivers(message):
#     user_state(message, "driver_menu")
#     query = get_driver_info()
#     columns, drivers_data = get_data_from_db(query)
#     send_page(message.chat.id, page=1, data=drivers_data, columns=columns, items_per_page=8, context="drivers")