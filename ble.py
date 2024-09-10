import asyncio
import requests
from bleak import BleakClient

async def read_ble_device(mac_address):
    async with BleakClient(mac_address) as client:
        while True:
            # Read the value of the characteristic
            value = await client.read_gatt_char("beb5483e-36e1-4688-b7f5-ea07361b26a8")
            #convert to string
            data = value.decode("utf-8")
            
            #print("Health Data:", data)  

            # Parse the data
            parsed_data = parse_health_data(data)
            #remove in production code
            print(parsed_data)
            
            await send_data_to_nodejs(parsed_data)

            await asyncio.sleep(1)  

# Function to parse health data
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

# Function to send data to Node.js backend
async def send_data_to_nodejs(data):
    url = "https://cms-backend-five.vercel.app/api/ble/esp"
    try:
        response = requests.post(url, json=data)
        print(response.text)
    except Exception as e:
        print("Error sending data to Node.js:", e)

async def main():
    #replace this by MAC id of your device
    mac_address = "A8:42:E3:4A:A3:BE"

    await read_ble_device(mac_address)

asyncio.run(main())
