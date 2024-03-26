import asyncio
from bleak import BleakClient
MAC_ADDRESS = "A8:42:E3:4A:A3:BE"

# UUIDs of the service and characteristics
SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
CHARACTERISTIC_UUID_1 = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
CHARACTERISTIC_UUID_2 = "1c95d5e3-d8f7-413a-bf3d-7a2e5d7be87e"

# Convert received hex data to a string
def hex_to_string(hex_data):
    return bytes(hex_data).decode("utf-8")


async def handle_data(sender, data):
    if sender == CHARACTERISTIC_UUID_1:
        print("Characteristic 1 Value:", hex_to_string(data))
    elif sender == CHARACTERISTIC_UUID_2:
        print("Characteristic 2 Value:", hex_to_string(data))


async def run():
    # Connect to the ESP device
    client = BleakClient(MAC_ADDRESS)
    await client.connect()

   
    await client.start_notify(CHARACTERISTIC_UUID_1, handle_data)
    await client.start_notify(CHARACTERISTIC_UUID_2, handle_data)

    # Keep the program running to continuously receive notifications
    while True:
        await asyncio.sleep(1)

asyncio.run(run())
