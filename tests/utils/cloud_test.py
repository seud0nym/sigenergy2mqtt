import asyncio
import os
import sys

from dotenv import load_dotenv

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud import SigenergyCloudClient


async def async_main():
    load_dotenv(dotenv_path="tests/utils/.debug.env")

    username = os.getenv("SIGENERGY2MQTT_CLOUD_USERNAME")
    password = os.getenv("SIGENERGY2MQTT_CLOUD_PASSWORD")
    region = os.getenv("SIGENERGY2MQTT_CLOUD_REGION")
    if username is None or password is None or region is None:
        raise ValueError("Missing required environment variables")

    client = SigenergyCloudClient(
        username,
        password,
        region=region,
    )
    try:
        await client.connect()

        data = await client._station_data(
            "GET",
            "device/aio/by/station",
            station_query=True,
        )
        print(data)

        # print(await client.aio_serials())

        # print(await client.device_topology())

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(async_main())
