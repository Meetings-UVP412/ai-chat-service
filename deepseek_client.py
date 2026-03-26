import requests
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import Config

logger = logging.getLogger(__name__)


class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = Config.DEEPSEEK_API_URL):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'ai-chat-service/1.0'
        })

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError))
    )
    def summarize(self, full_text: str, meeting_uuid: str) -> str:
        """Создаёт суммаризацию текста встречи"""
        truncated_text = full_text[:12000] if len(full_text) > 12000 else full_text

        prompt = f"""Ты — профессиональный ассистент для анализа встреч.
Проанализируй текст встречи и создай структурированную суммаризацию на русском языке.

Требования:
1. Выдели 3-5 ключевых тем обсуждения
2. Перечисли принятые решения (если есть)
3. Укажи задачи/действия с ответственными (если упомянуты)
4. Сохрани деловой стиль, без "воды"

Текст встречи:
{truncated_text}
"""

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ты — полезный ассистент для суммаризации деловых встреч."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

        try:
            logger.info(f"Отправка запроса к DeepSeek для встречи {meeting_uuid}")
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            summary = result['choices'][0]['message']['content'].strip()
            logger.info(f"Суммаризация получена для встречи {meeting_uuid}")
            return summary

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                logger.warning(f"rate limit превышен для {meeting_uuid}")
            elif response.status_code == 401:
                logger.error("Неверный API ключ DeepSeek!")
                logger.error(f"DeepSeek API error ({response.status_code}): {response.text[:300]}")
        except Exception as e:
            logger.exception(f"Ошибка при суммаризации через DeepSeek: {e}")
