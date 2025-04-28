import telebot
from loguru import logger
import os
import time
from telebot.types import InputFile
from polybot.img_proc import Img


class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)

        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        if "text" in msg:
            # if it is a normal text message
            self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')
        elif "caption" in msg:
            # if it is a photo with a caption
            self.send_text(msg['chat']['id'], f'Your photo caption: {msg["caption"]}')
        elif "photo" in msg:
            # if it is a photo without caption
            self.send_text(msg['chat']['id'], "I received a photo without caption!")
        else:
            self.send_text(msg['chat']['id'], "I received something else.")


class QuoteBot(Bot):
    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if msg["text"] != 'Please don\'t quote me':
            self.send_text_with_quote(msg['chat']['id'], msg["text"], quoted_msg_id=msg["message_id"])


class ImageProcessingBot(Bot):
    # Dictionary to store pending images for concatenation (keyed by chat_id)
    pending_concat = {}

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        chat_id = msg['chat']['id']

        if "photo" in msg:
            # Check if the caption is "concat" (for concatenation of two different images)
            if "caption" in msg and msg["caption"].lower() == "concat":
                # If no pending image stored for this chat, then store the current photo
                if chat_id not in ImageProcessingBot.pending_concat:
                    img_path = self.download_user_photo(msg)
                    ImageProcessingBot.pending_concat[chat_id] = img_path
                    self.send_text(chat_id,
                                   "First image received. Please send the second image with caption 'concat' to complete concatenation.")
                    return
                else:
                    # Retrieve the first image and clear the pending entry
                    first_img_path = ImageProcessingBot.pending_concat.pop(chat_id)
                    second_img_path = self.download_user_photo(msg)

                    # Load both images using the Img class
                    first_img = Img(first_img_path)
                    second_img = Img(second_img_path)

                    # Perform concatenation horizontally (change direction if you wish)
                    first_img.concat(second_img, direction='horizontal')

                    # Save the result
                    result_path = first_img.save_img()

                    # Send the concatenated image with a nice caption
                    self.send_photo(chat_id, result_path, caption="🖼️ Here is your beautifully concatenated image! 🖼️")
                    return

            # Process other photo commands (rotate, blur, etc.)
            else:
                try:
                    img_path = self.download_user_photo(msg)
                    img = Img(img_path)

                    if "caption" in msg:
                        caption = msg["caption"].lower()

                        if caption == "rotate":
                            img.rotate()
                            nice_message = "🎉 Your photo has been rotated beautifully! 🎉"
                        elif caption == "blur":
                            img.blur()
                            nice_message = "🌸 Your photo is now softly blurred! 🌸"
                        elif caption == "salt and pepper":
                            img.salt_n_pepper()
                            nice_message = "✨ A sprinkle of salt & pepper magic added! ✨"
                        elif caption == "segment":
                            img.segment()
                            nice_message = "🖌️ Your photo has been segmented artistically! 🖌️"
                        elif caption == "contour":
                            img.contour()
                            nice_message = "🎨 Contour filter applied to your photo! 🎨"
                        else:
                            self.send_text(chat_id,
                                           "❗ Unknown caption. Try: Rotate, Blur, Salt and Pepper, Segment, Contour, or Concat.")
                            return

                        result_path = img.save_img()
                        self.send_photo(chat_id, result_path)
                        self.send_text(chat_id, nice_message)
                    else:
                        self.send_text(chat_id, "⚡ Please add a caption to process your photo.")
                except Exception as e:
                    logger.error(f"Error processing image: {e}")
                    self.send_text(chat_id, "An error occurred while processing your image. Please try again later.")
        else:
            self.send_text(chat_id, "🤖 Please send me a photo.")
