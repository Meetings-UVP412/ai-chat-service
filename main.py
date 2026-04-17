from dotenv import load_dotenv
import os
from config import Config
from services.deepseek_client import DeepSeekClient
from services.meetings_client import MeetingsClient


def main():
    load_dotenv()

    print("DEEPSEEK_API_KEY from env:", os.environ.get('DEEPSEEK_API_KEY', 'NOT SET')[:10] + "...")

    meetings_client = MeetingsClient(Config.MEETINGS_API_URL)
    deepseek_client = DeepSeekClient(Config.DEEPSEEK_API_KEY)


if __name__ == "__main__":
    main()
