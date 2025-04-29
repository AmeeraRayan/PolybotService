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
    def __init__(self, token, telegram_chat_url):
        super().__init__(token, telegram_chat_url)
        self.pending_concat_image_path = None  # To store the first image temporarily

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if "text" in msg:
            user_text = msg["text"].strip().lower()
            if user_text in ["hi", "hello", "hey"]:
                self.send_text(
                    msg['chat']['id'],
                    "👋 Hi there! Send me a photo with a caption like `rotate`, `blur`, `segment`, `salt and pepper`, `contour`, or `concat`, and I’ll apply the effect for you! ✨"
                )
                return
            else:
                self.send_text(
                    msg['chat']['id'],
                    "🤖 I'm here to help you filter photos! Please send a photo with one of these captions: `rotate`, `blur`, `segment`, `salt and pepper`, `contour`, or `concat`."
                )
                return

        if "photo" in msg:
            try:
                img_path = self.download_user_photo(msg)
                img = Img(img_path)

                if "caption" in msg:
                    caption = msg["caption"].lower()

                    if caption == "rotate":
                        img.rotate()
                        nice_message = "🔄 Your photo has been rotated beautifully! 🔄"
                    elif caption == "blur":
                        img.blur()
                        nice_message = "🌫️ Your photo has been blurred artistically! 🌫️"
                    elif caption == "salt and pepper":
                        img.salt_n_pepper()
                        nice_message = "✨ A sprinkle of salt & pepper magic added! ✨"
                    elif caption == "segment":
                        img.segment()
                        nice_message = "🎨 Your photo has been segmented artistically! 🎨"
                    elif caption == "contour":
                        img.contour()
                        nice_message = "🖌️ Contour filter applied to your photo! 🖌️"
                    elif caption == "concat":
                        if self.pending_concat_image_path is None:
                            # First image received, wait for the second one
                            self.pending_concat_image_path = img_path
                            self.send_text(msg['chat']['id'],
                                           "✅ First image received. Please send the second image with caption 'concat' to complete concatenation.")
                            return
                        else:
                            # Second image received
                            another_img = Img(self.pending_concat_image_path)
                            img.concat(another_img, direction='horizontal')
                            nice_message = "🖼️ Your images have been concatenated side by side! 🖼️"
                            # Clear pending image after concatenation
                            self.pending_concat_image_path = None
                    else:
                        self.send_text(msg['chat']['id'],
                                       "❗ Unknown caption. Try: Rotate, Blur, Salt and Pepper, Segment, Contour, or Concat.")
                        return

                    # Save and send back the processed image
                    img_path = img.save_img()
                    self.send_photo(msg['chat']['id'], img_path)

                    # Send a beautiful success message
                    self.send_text(msg['chat']['id'], nice_message)

                else:
                    self.send_text(msg['chat']['id'], "Please add a caption to process your photo.")

            except Exception as e:
                logger.error(f"Error processing image: {e}")
                self.send_text(msg['chat']['id'],
                               "❗ An error occurred while processing your image. Please try again later.")

        else:
            self.send_text(msg['chat']['id'], "Please send me a photo.")
