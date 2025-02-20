import os, telebot, os, zipfile, tempfile, operations_on_tables as oot
from dotenv import load_dotenv

load_dotenv()
bot_token = os.getenv("BOT_TOKEN")
admin_ids_str  = os.getenv("ADMIN_IDS")
admin_ids = [int(ID.strip()) for ID in admin_ids_str.split(',')]


bot = telebot.TeleBot(bot_token)


def create_zip_and_save(user_images, user_id, vin):
    """Creates a ZIP file with all user images and saves it."""

    # Ensure the user has images
    if user_id not in user_images or not user_images[user_id]["images"]:
        bot.send_message(user_id, "No images to zip. Please upload at least one.")
        return None

    image_files = user_images[user_id]["images"]
    zip_filename = f"documents/{vin}_documents.zip"  # Define the zip path

    # Ensure 'documents' directory exists
    os.makedirs("documents", exist_ok=True)

    # Use a temporary directory to store downloaded images
    with tempfile.TemporaryDirectory() as tmpdirname:
        for idx, file_id in enumerate(image_files):
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            # Save the image with a proper filename
            image_path = os.path.join(tmpdirname, f"{vin}_image_{idx + 1}.jpg")
            with open(image_path, "wb") as f:
                f.write(downloaded_file)

        # Create a ZIP file with all images
        with zipfile.ZipFile(zip_filename, "w") as zipf:
            for idx in range(len(image_files)):
                image_file_path = os.path.join(tmpdirname, f"{vin}_image_{idx + 1}.jpg")
                zipf.write(image_file_path, os.path.basename(image_file_path))

    user_images.pop(user_id, None)  # Clear stored images

    bot.send_message(user_id, "Your images have been successfully uploaded and packed into a ZIP file.")
    return zip_filename  # Return the final zip path


def unzip_and_send_files(user_id, zip_filename):
    """Extracts the ZIP file and sends all images to the user."""

    # Ensure the ZIP file exists before proceeding
    if not os.path.exists(zip_filename):
        bot.send_message(user_id, "The requested ZIP file was not found.")
        return

    # Create a temporary directory to extract files
    with tempfile.TemporaryDirectory() as tmpdirname:
        with zipfile.ZipFile(zip_filename, "r") as zipf:
            zipf.extractall(tmpdirname)

        # Send each extracted image to the user
        sent_files = []
        for root, _, files in os.walk(tmpdirname):
            for file in sorted(files):  # Ensure images are sent in order
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    if user_id in admin_ids:
                        for admins in admin_ids:
                            sent_files.append(bot.send_document(admins, f))
                    else:
                        for admins in admin_ids + user_id:
                            sent_files.append(bot.send_document(admins, f))

    if sent_files:
        bot.send_message(user_id, "All images have been successfully extracted and sent.")
    else:
        bot.send_message(user_id, "No images were found inside the ZIP file.")
