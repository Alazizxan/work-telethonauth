import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BASE_WEBHOOK_URL = os.getenv("BASE_WEBHOOK_URL")


USE_PROXY = False

PROXY_CONFIG = {
    "proxy_type": "socks5",
    "addr": "127.0.0.1",
    "port": 1080,
    "username": None,
    "password": None,
}