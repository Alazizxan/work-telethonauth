import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
REDIS_URL = os.getenv("REDIS_URL")
BASE_WEBHOOK_URL = os.getenv("BASE_WEBHOOK_URL")
