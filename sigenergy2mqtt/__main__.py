import asyncio
import logging

from sigenergy2mqtt.config import Config, initialize
from sigenergy2mqtt.main import async_main


def main():
    initialize()
    asyncio.run(async_main(), debug=True if Config.log_level == logging.DEBUG else False)
