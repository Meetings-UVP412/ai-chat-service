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
