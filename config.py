import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY_RAW = os.getenv('DEEPSEEK_API_KEY')
print(f"[DEBUG] DEEPSEEK_API_KEY loaded: {bool(DEEPSEEK_API_KEY_RAW)}")
print(f"[DEBUG] Key length: {len(DEEPSEEK_API_KEY_RAW) if DEEPSEEK_API_KEY_RAW else 0}")


class Config:
    RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))
    RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
    RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'guest')

    MEETINGS_API_URL = os.getenv('MEETINGS_API_URL', 'http://localhost:8100')

    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')

    EXCHANGE_NAME = 'meetings-exchange'
    CHUNK_PROCESSED_ROUTING_KEY = 'chunk.processed'
    SUMMARY_ROUTING_KEY = 'meeting.summarized'
    QUEUE_NAME = 'ai_chat_queue'
