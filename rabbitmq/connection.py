import pika
from config import Config


def connect_rabbitmq():
    credentials = pika.PlainCredentials(Config.RABBITMQ_USER, Config.RABBITMQ_PASSWORD)
    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=Config.RABBITMQ_HOST,
            port=Config.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
    )


def declare_queue(channel):
    channel.exchange_declare(exchange=Config.EXCHANGE_NAME, exchange_type='topic', durable=True)
    channel.queue_declare(queue=Config.QUEUE_NAME, durable=True)
    channel.queue_bind(
        exchange=Config.EXCHANGE_NAME,
        queue=Config.QUEUE_NAME,
        routing_key=Config.CHUNK_PROCESSED_ROUTING_KEY
    )
