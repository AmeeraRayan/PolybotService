import boto3
import os
import json
from decimal import Decimal

class DynamoDBStorage:
    def init(self):
        self.table_name = os.getenv("DYNAMODB_TABLE", "Predictions")
        self.region = os.getenv("AWS_REGION", "eu-north-1")
        self.dynamodb = boto3.resource("dynamodb", region_name=self.region)
        self.table = self.dynamodb.Table(self.table_name)

    def get_prediction(self, uid):
        try:
            response = self.table.get_item(Key={'uid': uid})
            item = response.get('Item')
            if not item:
                return None
            return {
                "prediction_uid": item.get("uid"),
                "original_image": item.get("original_image"),
                "predicted_image": item.get("predicted_image"),
                "labels": json.loads(item.get("labels", "[]")),
                "score": float(item.get("score", 0)),
                "box": json.loads(item.get("box", "[]")),
                "timestamp": item.get("timestamp"),
                "chat_id": item.get("chat_id")  # make sure YOLO service saves this
            }
        except Exception as e:
            print(f"[ERROR] get_prediction failed: {e}")
            return None