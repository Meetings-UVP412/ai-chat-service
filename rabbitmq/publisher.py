import pika
import json
from datetime import datetime
from config import Config


def publish_summary_result(channel, uuid: str, summary: str, success: bool, ord: int):
    result = {
        "uuid": uuid,
        "ord": ord,
        "summary": summary if success else "",
        "success": success,
        "timestamp": datetime.now().isoformat()
    }

    channel.basic_publish(
        exchange=Config.EXCHANGE_NAME,
        routing_key=Config.SUMMARY_ROUTING_KEY,
        body=json.dumps(result, ensure_ascii=False).encode('utf-8'),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type='application/json',
            content_encoding='utf-8'
        )
    )
