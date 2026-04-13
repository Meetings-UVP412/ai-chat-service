import pika
import json
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, Any
from config import Config
from deepseek_client import DeepSeekClient
from meetings_client import MeetingsClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

rabbit_connection = None
meetings_client = None
deepseek_client = None
shutdown_flag = False


class ChunkProcessedEvent:
    def __init__(self, uuid: str, ord_num: int, is_last: bool, duration: int, success: bool):
        self.uuid = uuid
        self.ord = ord_num
        self.isLast = is_last
        self.duration = duration
        self.success = success

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            uuid=str(data.get('uuid') or data.get('UUID') or ''),
            ord_num=int(data.get('ord', data.get('Ord', 0))),
            is_last=bool(data.get('isLast', data.get('islast', False))),
            duration=int(data.get('duration', data.get('Duration', 0))),
            success=bool(data.get('success', False))
        )


def handle_signal(signum, frame):
    global shutdown_flag
    logger.info(f"Получен сигнал завершения {signum}")
    shutdown_flag = True
    if rabbit_connection and rabbit_connection.is_open:
        rabbit_connection.close()


def publish_summary_result(channel, uuid: str, summary: str, success: bool):
    result = {
        "uuid": uuid,
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
    logger.info(f"Результат суммаризации опубликован: {Config.SUMMARY_ROUTING_KEY}")


def process_chunk_event(channel, event: ChunkProcessedEvent):
    logger.info(f"Обработка события: {event.uuid}, чанк {event.ord}, isLast={event.isLast}")

    if not event.isLast:
        logger.info(f"Чанк {event.ord} не последний!")
        return

    if not event.success:
        logger.warning(f"Транскрипция неуспешна для {event.uuid}!")
        return

    try:
        # Получаем полный текст встречи из redis
        full_text = meetings_client.get_full_meeting_text(event.uuid)
        logger.warning(f"Текст встречи: {full_text}")

        if not full_text or len(full_text.strip()) < 1:
            logger.warning(f"Текст встречи {event.uuid} пустой!")
            logging.warning(full_text)
            publish_summary_result(channel, event.uuid, "Текст встречи пустой!", False)
            return

        # Суммаризация
        summary = deepseek_client.summarize(full_text, event.uuid)

        # Сохраняем в postgres
        if meetings_client.save_summary(event.uuid, summary):
            publish_summary_result(channel, event.uuid, summary, True)
            logger.info(f"Суммаризация завершена для встречи {event.uuid}")
        else:
            logger.error(f"Не удалось сохранить суммаризацию для {event.uuid}")
            publish_summary_result(channel, event.uuid, "Ошибка сохранения суммаризации", False)

    except Exception as e:
        logger.exception(f"Критическая ошибка при обработке встречи {event.uuid}: {e}")
        publish_summary_result(channel, event.uuid, f"Ошибка суммаризации: {str(e)}", False)


def callback(ch, method, properties, body):
    if shutdown_flag:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        return

    logger.info(f"\n{'='*70}")
    logger.info(f"Получено сообщение (delivery_tag={method.delivery_tag})")

    try:
        data = json.loads(body.decode('utf-8'))
        event = ChunkProcessedEvent.from_dict(data)
        logger.info(f"Распаршено событие: uuid={event.uuid}, ord={event.ord}, isLast={event.isLast}")

        process_chunk_event(ch, event)

        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Сообщение {method.delivery_tag} подтверждено")

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logger.exception(f"Ошибка обработки сообщения: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


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
    logger.info(f"Очередь '{Config.QUEUE_NAME}' привязана к exchange '{Config.EXCHANGE_NAME}' "
                f"с routing key '{Config.CHUNK_PROCESSED_ROUTING_KEY}'")


def main():
    global rabbit_connection, meetings_client, deepseek_client

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("="*70)
    logger.info("Запуск AI Chat Service")
    logger.info("="*70)

    meetings_client = MeetingsClient(Config.MEETINGS_API_URL)
    deepseek_client = DeepSeekClient(Config.DEEPSEEK_API_KEY)

    try:
        rabbit_connection = connect_rabbitmq()
        channel = rabbit_connection.channel()
        declare_queue(channel)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=Config.QUEUE_NAME, on_message_callback=callback)

        logger.info("\nСервис готов к обработке сообщений")
        logger.info(f"   Слушает: {Config.CHUNK_PROCESSED_ROUTING_KEY}")
        logger.info(f"   Публикует: {Config.SUMMARY_ROUTING_KEY}")
        logger.info("="*70)

        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        logger.critical(f"Не удалось подключиться к RabbitMQ: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nСервис остановлен пользователем")
    finally:
        if rabbit_connection and rabbit_connection.is_open:
            rabbit_connection.close()
            logger.info("Соединение с RabbitMQ закрыто!")


if __name__ == "__main__":
    main()
