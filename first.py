import asyncio
from bleak import BleakClient
#this code is able to fetch data
async def read_ble_device(mac_address):
    async with BleakClient(mac_address) as client:
        while True:
            # Read the value of the characteristic
            value = await client.read_gatt_char("beb5483e-36e1-4688-b7f5-ea07361b26a8")
            print("Health Data:", value.decode("utf-8"))  # Convert bytes to string

            await asyncio.sleep(1)  

async def main():
    mac_address = "A8:42:E3:4A:A3:BE"

    await read_ble_device(mac_address)

asyncio.run(main())
