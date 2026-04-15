import requests
import logging
import json
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
    def generate_response(self, messages: list, temperature: float = 0.3, max_tokens: int = 1000) -> str:
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            return content

        except Exception as e:
            logger.exception(f"Ошибка при генерации ответа: {e}")
            raise

    def stream_response(self, messages: list, temperature: float = 0.3, max_tokens: int = 1000):
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        try:
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=60,
                stream=True
            )
            response.raise_for_status()

            full_response = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        chunk_data = decoded_line[6:]
                        if chunk_data.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(chunk_data)
                            delta = data["choices"][0]["delta"]
                            content = delta.get("content", "")
                            if content:
                                full_response += content
                                yield content
                        except (KeyError, json.JSONDecodeError):
                            continue

            return full_response

        except Exception as e:
            logger.exception(f"Ошибка при стриминге: {e}")
            raise

    def summarize(self, full_text: str, meeting_uuid: str) -> str:
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

        messages = [
            {"role": "system", "content": "Ты — полезный ассистент для суммаризации деловых встреч."},
            {"role": "user", "content": prompt}
        ]

        return self.generate_response(messages, temperature=0.3, max_tokens=1000)