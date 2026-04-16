import logging
from config import Config
from services.meetings_client import MeetingsClient
from services.deepseek_client import DeepSeekClient
from services.summarize_service import SummarizeService
from utils.signal_handler import setup_signal_handlers

meetings_client = MeetingsClient(Config.MEETINGS_API_URL)
deepseek_client = DeepSeekClient(Config.DEEPSEEK_API_KEY)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def main():
    setup_signal_handlers()

    logger.info("Запуск AI Chat Service")
    service = SummarizeService(meetings_client, deepseek_client)
    service.start()


if __name__ == "__main__":
    main()
