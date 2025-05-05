import telebot
from loguru import logger
import os
import time
import requests  # 🆕 for communicating with YOLO service
from telebot.types import InputFile
from polybot.img_proc import Img


class Bot:

    def __init__(self, token, telegram_chat_url):
        self.telegram_bot_client = telebot.TeleBot(token)
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=60)
        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
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

        self.telegram_bot_client.send_photo(chat_id, InputFile(img_path))

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')
        if "text" in msg:
            self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')
        elif "caption" in msg:
            self.send_text(msg['chat']['id'], f'Your photo caption: {msg["caption"]}')
        elif "photo" in msg:
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
        self.pending_concat_image_path = None

    def handle_message(self, msg):
        logger.info(f'Incoming message: {msg}')

        if "text" in msg:
            user_text = msg["text"].strip().lower()
            if user_text in ["hi", "hello", "hey"]:
                self.send_text(
                    msg['chat']['id'],
                    "👋 Hi there! Send me a photo with a caption like `rotate`, `blur`, `segment`, `salt and pepper`, `contour`, `concat`, or `detect`, and I’ll apply the effect or tell you what I see! 🤖"
                )
                return
            else:
                self.send_text(
                    msg['chat']['id'],
                    "🤖 I'm here to help you filter photos! Please send a photo with one of these captions: `rotate`, `blur`, `segment`, `salt and pepper`, `contour`, `concat`, or `detect`."
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
                            self.pending_concat_image_path = img_path
                            self.send_text(msg['chat']['id'],
                                           "✅ First image received. Please send the second image with caption 'concat' to complete concatenation.")
                            return
                        else:
                            another_img = Img(self.pending_concat_image_path)
                            img.concat(another_img, direction='horizontal')
                            nice_message = "🖼️ Your images have been concatenated side by side! 🖼️"
                            self.pending_concat_image_path = None
                    elif caption == "detect":
                        try:
                            with open(img_path, 'rb') as f:
                                response = requests.post("http://localhost:8080/predict", files={"file": f})
                                response.raise_for_status()
                            data = response.json()
                            labels = data.get("labels", [])
                            if labels:
                                nice_message = "🧠 Detected objects: " + ", ".join(labels)
                            else:
                                nice_message = "🔍 No objects detected."
                        except Exception as e:
                            logger.error(f"Failed to get predictions from YOLO: {e}")
                            nice_message = "❗ Error occurred while contacting YOLO service."
                    else:
                        self.send_text(msg['chat']['id'],
                                       "❗ Unknown caption. Try: Rotate, Blur, Salt and Pepper, Segment, Contour, Concat, or Detect.")
                        return

                    img_path = img.save_img()
                    self.send_photo(msg['chat']['id'], img_path)
                    self.send_text(msg['chat']['id'], nice_message)

                else:
                    self.send_text(msg['chat']['id'], "Please add a caption to process your photo.")

            except Exception as e:
                logger.error(f"Error processing image: {e}")
                self.send_text(msg['chat']['id'], "❗ An error occurred while processing your image. Please try again later.")
        else:
            self.send_text(msg['chat']['id'], "Please send me a photo.")
