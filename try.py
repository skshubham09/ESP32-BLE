import asyncio
import requests
import websockets
from bleak import BleakClient

# Define the UUIDs for the characteristics
READ_CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
WRITE_CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a9"

async def read_ble_device(client):
    while True:
        try:
            # Read the value of the characteristic
            value = await client.read_gatt_char(READ_CHARACTERISTIC_UUID)
            data = value.decode("utf-8")
            parsed_data = parse_health_data(data)
            print(parsed_data)
            await send_data_to_nodejs(parsed_data)
        except Exception as e:
            print(f"Error reading BLE device: {e}")
        await asyncio.sleep(1)

async def write_ble_device(client, message):
    try:
        await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, message.encode("utf-8"))
    except Exception as e:
        print(f"Error writing to BLE device: {e}")

def parse_health_data(data):
    split_data = data.split('.')
    temperature = float(split_data[0])
    hrv = float(split_data[1])
    hr = float(split_data[2])
    rr = float(split_data[3])
    spo2 = float(split_data[4])
    return {
        "id": "LA10AH0001",
        "temperature": temperature,
        "hr": hr,
        "hrv": hrv,
        "rr": rr,
        "spo2": spo2
    }

async def send_data_to_nodejs(data):
    url = "https://cms-backend-five.vercel.app/api/ble/esp"
    try:
        response = requests.post(url, json=data)
        print(response.text)
    except Exception as e:
        print(f"Error sending data to Node.js: {e}")

async def websocket_handler(websocket, path, client):
    async for message in websocket:
        print(f"Received message from websocket: {message}")
        await write_ble_device(client, message)

async def start_websocket_server(client):
    async with websockets.serve(lambda ws, path: websocket_handler(ws, path, client), "localhost", 8080):
        await asyncio.Future()  # run forever

async def main():
    mac_address = "A8:42:E3:4A:A3:BE"
    async with BleakClient(mac_address) as client:
        await asyncio.gather(
            read_ble_device(client),
            start_websocket_server(client)
        )

asyncio.run(main())
