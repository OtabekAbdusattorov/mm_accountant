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
        try:
            with zipfile.ZipFile(zip_filename, "r") as zipf:
                zipf.extractall(tmpdirname)

            sent_files = []
            for root, _, files in os.walk(tmpdirname):
                for file in sorted(files):  # Ensure images are sent in order
                    file_path = os.path.join(root, file)

                    # **Check if file exists and is non-empty**
                    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                        bot.send_message(user_id, f"Skipping empty or missing file: {file}")
                        continue  # Skip empty files

                    with open(file_path, "rb") as f:
                        bot.send_document(user_id, f)

                    sent_files.append(file_path)

            # Send confirmation message if files were sent
            if sent_files:
                bot.send_message(user_id, "All images have been successfully extracted and sent.")
            else:
                bot.send_message(user_id, "No valid images were found inside the ZIP file.")

        except zipfile.BadZipFile:
            bot.send_message(user_id, "The ZIP file is corrupted and cannot be opened.")
        except Exception as e:
            bot.send_message(user_id, f"An error occurred while processing the ZIP file: {str(e)}")

