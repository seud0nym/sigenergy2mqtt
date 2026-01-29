import asyncio
import logging

from sigenergy2mqtt.config import Config
from sigenergy2mqtt.main import async_main


def main():
    asyncio.run(async_main(), debug=True if Config.log_level == logging.DEBUG else False)
