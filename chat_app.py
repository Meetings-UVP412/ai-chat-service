import os
from dotenv import load_dotenv

load_dotenv()

from config import Config
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from services.chat_service import ChatService
from services.meetings_client import MeetingsClient
from services.deepseek_client import DeepSeekClient

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
