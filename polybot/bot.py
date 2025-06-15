import boto3
import telebot
import logging
from boto3.s3.inject import upload_file
from botocore.exceptions import ClientError
from loguru import logger
import os
import time
import requests  # 🆕 for communicating with YOLO service
from telebot.types import InputFile
from polybot.img_proc import Img
import boto3
import json

class Bot:

    def __init__(self, token, telegram_chat_url):
        self.telegram_bot_client = telebot.TeleBot(token)
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)
        print(f"token: {token}")
        cert_file = os.environ.get('TELEGRAM_CERT_FILE' , 'polybot.crt')
        cert_path = os.path.join(os.path.dirname(__file__), 'certs', cert_file)
        self.telegram_bot_client.set_webhook(
            url=f'{telegram_chat_url}/{token}/',
            certificate=open(cert_path, 'rb'),
            timeout=60
        )
        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text):
        self.telegram_bot_client.send_message(chat_id, text)

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def upload_image_to_s3(self,bucket , file_name, object_name=None):
        """Upload a file to an S3 bucket"""
        if object_name is None:
            object_name = os.path.basename(file_name)

        s3_client = boto3.client('s3')  # משתמש בפרטי AWS שכבר מוגדרים עם aws configure
        try:
            response = s3_client.upload_file(file_name, bucket, object_name)
        except ClientError as e:
            logging.error(e)
            return False
        return True

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
                            nice_message = "🖼️ Yourrr images have been concatenated side by side! 🖼️"
                            self.pending_concat_image_path = None
                    elif caption == "detect":
                        try:
                            file_name = os.path.basename(img_path)
                            bucket_name = os.environ["S3_BUCKET_NAME"]
                            region_name="eu-north-1"
                            success=self.upload_image_to_s3(bucket_name ,img_path,file_name)
                            if not success:
                                self.send_text(msg['chat']['id'],"! Failed to upload image to S3.")
                                return
                            print("Sending to Yolo",file_name, bucket_name,region_name)
                            queue_url = os.environ["SQS_QUEUE_URL"]
                            produce_message_to_sqs(
                                {"image_name": file_name, "bucket_name": bucket_name, "region_name": region_name},
                                queue_url=queue_url,
                                region=region_name
                            )
                            nice_message = "🕐 Your image was uploaded and is being processed... Please wait a moment."
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

def produce_message_to_sqs(message_body: dict, queue_url: str, region: str):
    sqs = boto3.client("sqs", region_name=region)
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )
        print(f"✅ Message sent to SQS. ID: {response['MessageId']}")
    except ClientError as e:
        print(f"❌ Failed to send message to SQS: {e}")