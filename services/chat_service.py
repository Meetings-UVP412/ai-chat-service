import logging
from .instructions import INSTRUCTIONS, DEFAULT_PROMPT

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, meetings_client, deepseek_client):
        self.meetings_client = meetings_client
        self.deepseek_client = deepseek_client

    def create_chats_after_summarization(self, meeting_uuid: str, transcription: str):

        for title, instruction in INSTRUCTIONS:
            try:
                prompt = f"{instruction}\n\nТранскрипция встречи:\n{transcription}"
                messages = [
                    {"role": "system", "content": DEFAULT_PROMPT},
                    {"role": "user", "content": prompt}
                ]

                response = self.deepseek_client.generate_response(messages)
                logger.info(f"DEEPSEEK RESPONSE {response}")

                chat_data = {
                    "meetingUUID": meeting_uuid,
                    "name": title,
                    "firstMessage": {
                        "role": "assistant",
                        "content": response
                    }
                }

                self.meetings_client.create_chat(chat_data)
                logger.info(f"Создан чат '{title}' для встречи {meeting_uuid}")

            except Exception as e:
                logger.exception(f"Ошибка при создании чата '{title}': {e}")

    def stream_chat_response(self, chat_id: str, user_message: dict):
        try:
            chat_info = self.meetings_client.get_chat(chat_id)
            current_messages = chat_info.get('messages', [])
            meeting_uuid = chat_info.get('meetingUUID', '')

            transcription = "Транскрипция встречи: " + self.meetings_client.get_full_meeting_text(meeting_uuid)
            logger.info(f"GOT TRANSCRIPTION FOR STREAM RESPONSE: {transcription}")

            messages = [{"role": "system", "content": DEFAULT_PROMPT + transcription}]
            messages.extend(current_messages)
            messages.append(user_message)

            full_response = ""
            for token in self.deepseek_client.stream_response(messages):
                full_response += token
                logger.info(token)
                yield f"data: {token}\n\n"

            # убираем системный промпт
            updated_messages = messages[1:] + [{"role": "assistant", "content": full_response}]
            self.meetings_client.update_chat_messages(chat_id, updated_messages)

        except Exception as e:
            logger.exception(f"Ошибка при стриминге чата {chat_id}: {e}")
            yield f"data: Ошибка: {str(e)}\n\n"
