import pika
import json
import logging
from models.events import ChunkProcessedEvent
from rabbitmq.connection import connect_rabbitmq, declare_queue
from rabbitmq.publisher import publish_summary_result
from utils.signal_handler import get_shutdown_flag
from config import Config

logger = logging.getLogger(__name__)


class SummarizeService:
    def __init__(self, meetings_client, deepseek_client):
        self.meetings_client = meetings_client
        self.deepseek_client = deepseek_client
        self.connection = None

    def process_chunk_event(self, channel, event: ChunkProcessedEvent):
        logger.info(f"Обработка события: {event.uuid}, чанк {event.ord}, isLast={event.isLast}")

        if not event.isLast:
            logger.info(f"Чанк {event.ord} не последний!")
            return

        if not event.success:
            logger.warning(f"Транскрипция неуспешна для {event.uuid}!")
            return

        try:
            full_text = self.meetings_client.get_full_meeting_text(event.uuid)
            logger.warning(f"Транскрипция встречи: {full_text}")

            if not full_text or len(full_text.strip()) < 1:
                logger.warning(f"Транскрипция встречи {event.uuid} пустая!")
                publish_summary_result(channel, event.uuid, "Транскрипция встречи пустая!", False)
                return

            summary = self.deepseek_client.summarize(full_text, event.uuid)
            publish_summary_result(channel, event.uuid, summary, True)
            logger.info(f"Суммаризация завершена для встречи: {event.uuid}")

        except Exception as e:
            logger.exception(f"Критическая ошибка при обработке встречи {event.uuid}: {e}")
            publish_summary_result(channel, event.uuid, f"Ошибка суммаризации: {str(e)}", False)

    def callback(self, ch, method, properties, body):
        if get_shutdown_flag():
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        logger.info(f"\n{'='*70}")
        logger.info(f"Получено сообщение (delivery_tag={method.delivery_tag})")

        try:
            data = json.loads(body.decode('utf-8'))
            event = ChunkProcessedEvent.from_dict(data)
            logger.info(f"Распаршено событие: uuid={event.uuid}, ord={event.ord}, isLast={event.isLast}")

            self.process_chunk_event(ch, event)

            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Сообщение {method.delivery_tag} подтверждено")

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.exception(f"Ошибка обработки сообщения: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start(self):
        try:
            self.connection = connect_rabbitmq()
            channel = self.connection.channel()
            declare_queue(channel)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=Config.QUEUE_NAME, on_message_callback=self.callback)

            logger.info("\nСервис готов к обработке сообщений")
            logger.info(f"   Слушает: {Config.CHUNK_PROCESSED_ROUTING_KEY}")
            logger.info(f"   Публикует: {Config.SUMMARY_ROUTING_KEY}")
            logger.info("="*70)

            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            logger.critical(f"Не удалось подключиться к RabbitMQ: {e}")
            raise
        finally:
            if self.connection and self.connection.is_open:
                self.connection.close()
                logger.info("Соединение с RabbitMQ закрыто!")
