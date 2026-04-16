import requests
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class MeetingsClient:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ai-chat-service/1.0',
        })

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    def get_full_meeting_text(self, uuid: str) -> str:
        url = f"{self.api_base_url}/internal/meetingResult/{uuid}"
        try:
            logger.info(f"Запрос транскрипции встречи: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            text = response.text.strip()
            logger.info(f"Получена транскрипция встречи: {uuid}")
            return text
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                logger.warning(f"Встреча не найдена: {uuid}")
            else:
                logger.error(f"Ошибка API при получении текста ({response.status_code}): {response.text[:200]}")
            raise
        except Exception as e:
            logger.exception(f"Ошибка сети при получении текста: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    def save_summary(self, uuid: str, summary: str) -> bool:
        logger.info(f"meeting: {uuid}, summary: {summary}")
        return True

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    def create_chat(self, chat_data: dict) -> bool:
        url = f"{self.api_base_url}/chats/create"
        try:
            response = self.session.post(url, json=chat_data, timeout=15)
            response.raise_for_status()
            logger.info(f"Чат создан успешно")
            return True
        except Exception as e:
            logger.exception(f"Ошибка при создании чата: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    def get_chat_messages(self, chat_id: str) -> list:
        url = f"{self.api_base_url}/chats/history/{chat_id}"
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            chat_data = response.json()
            return chat_data.get('messages', [])
        except Exception as e:
            logger.exception(f"Ошибка при получении сообщений чата {chat_id}: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    def update_chat_messages(self, chat_id: str, messages: list) -> bool:
        url = f"{self.api_base_url}/chats/{chat_id}/update-messages"
        try:
            response = self.session.post(
                url,
                json={"messages": messages},
                timeout=15
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.exception(f"Ошибка при обновлении сообщений чата {chat_id}: {e}")
            raise
