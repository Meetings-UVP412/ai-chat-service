import logging
from config import Config
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from services.chat_service import ChatService
from services.meetings_client import MeetingsClient
from services.deepseek_client import DeepSeekClient
from services.summarize_service import SummarizeService
from utils.signal_handler import setup_signal_handlers


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

app = FastAPI()

meetings_client = MeetingsClient(Config.MEETINGS_API_URL)
deepseek_client = DeepSeekClient(Config.DEEPSEEK_API_KEY)
chat_service = ChatService(meetings_client, deepseek_client)


@app.post("/internal/chat/{chat_id}/stream")
async def stream_chat_response(chat_id: str, request: Request):
    try:
        data = await request.json()
        user_message = data.get("message")

        if not user_message:
            raise HTTPException(status_code=400, detail="Нет сообщения пользователя")

        return StreamingResponse(
            chat_service.stream_chat_response(chat_id, user_message),
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.exception(f"Ошибка в стрим-запросе: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    logger.info("="*70)
    logger.info("Запуск AI Chat Service")
    logger.info("="*70)

    setup_signal_handlers()

    service = SummarizeService(meetings_client, deepseek_client)
    service.start()


if __name__ == "__main__":
    main()
