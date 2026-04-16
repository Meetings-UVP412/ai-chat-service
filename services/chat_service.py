import logging

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, meetings_client, deepseek_client):
        self.meetings_client = meetings_client
        self.deepseek_client = deepseek_client

    def create_chats_after_summarization(self, meeting_uuid: str, summary: str):
        instructions = [
            ("Краткое резюме", "Создай краткое резюме встречи на 3-5 предложений."),
            ("Задачи и действия", "Выдели список задач и действий с ответственными лицами."),
            ("Принятые решения", "Перечисли все принятые решения на встрече."),
            ("Риски и проблемы", "Опиши риски и проблемы, о которых говорили на встрече."),
            ("Следующие шаги", "Сформулируй следующие шаги и действия после встречи.")
        ]

        for title, instruction in instructions:
            try:
                prompt = f"{instruction}\n\nСуммаризация встречи:\n{summary}"
                messages = [
                    {"role": "system", "content": "Ты — полезный ассистент."},
                    {"role": "user", "content": prompt}
                ]

                response = self.deepseek_client.generate_response(messages)

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
            current_messages = self.meetings_client.get_chat_messages(chat_id)
            new_messages = current_messages + [user_message]

            full_response = ""
            for token in self.deepseek_client.stream_response(new_messages):
                full_response += token
                yield f"data: {token}\n\n"

            updated_messages = new_messages + [{"role": "assistant", "content": full_response}]
            self.meetings_client.update_chat_messages(chat_id, updated_messages)

        except Exception as e:
            logger.exception(f"Ошибка при стриминге чата {chat_id}: {e}")
            yield f"data: Ошибка: {str(e)}\n\n"
