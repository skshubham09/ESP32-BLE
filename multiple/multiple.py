import asyncio
import csv
import json
import requests
import websockets
from bleak import BleakClient

# Define the UUIDs for the characteristics
READ_CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
WRITE_CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a9"

async def read_ble_device(client, device_id):
    while True:
        try:
            # Read the value of the characteristic
            value = await client.read_gatt_char(READ_CHARACTERISTIC_UUID)
            data = value.decode("utf-8")
            parsed_data = parse_health_data(data, device_id)
            print(parsed_data)
            await send_data_to_nodejs(parsed_data)
        except Exception as e:
            print(f"Error reading BLE device {device_id}: {e}")
        await asyncio.sleep(1)

async def write_ble_device(client, message):
    try:
        await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, message.encode("utf-8"))
    except Exception as e:
        print(f"Error writing to BLE device: {e}")

def parse_health_data(data, device_id):
    split_data = data.split('.')
    temperature = float(split_data[0])
    hrv = float(split_data[1])
    hr = float(split_data[2])
    rr = float(split_data[3])
    spo2 = float(split_data[4])
    return {
        "id": device_id,
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

async def websocket_handler(websocket, path, clients):
    async for message in websocket:
        print(f"Received message from websocket: {message}")
        # Assuming message format: {"device_id": "A842E34AA3BE", "message": "HELP"}
        message_data = json.loads(message)
        device_id = message_data["device_id"]
        ble_message = message_data["message"]
        if device_id in clients:
            await write_ble_device(clients[device_id], ble_message)
        else:
            print(f"Device {device_id} not connected")

async def start_websocket_server(clients):
    async with websockets.serve(lambda ws, path: websocket_handler(ws, path, clients), "localhost", 8765):
        await asyncio.Future()  # run forever

def read_mac_addresses_from_csv(file_path):
    mac_addresses = []
    with open(file_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            mac_addresses.append(row["mac_address"])
    return mac_addresses

async def handle_device(mac_address):
    async with BleakClient(mac_address) as client:
        device_id = mac_address.replace(":", "")
        await asyncio.gather(
            read_ble_device(client, device_id)
        )

async def main():
    mac_addresses = read_mac_addresses_from_csv('mac_addresses.csv')
    clients = {mac.replace(":", ""): BleakClient(mac) for mac in mac_addresses}
    
    # Connect all clients and start their tasks
    tasks = [handle_device(mac) for mac in mac_addresses]
    await asyncio.gather(
        start_websocket_server(clients),
        *tasks
    )

asyncio.run(main())
