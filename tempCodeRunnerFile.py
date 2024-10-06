import asyncio
import re
import aiohttp
import serial_asyncio

API_URL = "https://cms-backend-five.vercel.app/api/ble/esp"
DEVICE_IDS = ['LA10AH0001', 'LA10AH0002']  # Device IDs for the two devices
PORTS = ['COM7', 'COM8']  # Serial ports corresponding to each device
ALERT_API_URL = "https://cms-backend-five.vercel.app/api/alert/readAlertReply"

# Keep track of the last message ID for each device
last_message_id = {device_id: None for device_id in DEVICE_IDS}

# Function to parse incoming data
def parse_data(data, device_id):
    parsed_data = {'id': device_id}

    # Extract values using regular expressions
    temp_match = re.search(r'Body temperature: (\d+)', data)
    if temp_match:
        parsed_data['bodyTemperature'] = int(temp_match.group(1))

    resp_match = re.search(r'Respiration rate: (\d+)', data)
    if resp_match:
        parsed_data['respiratoryRate'] = int(resp_match.group(1))

    heart_rate_match = re.search(r'Heart Rate: (\d+)', data)
    if heart_rate_match:
        parsed_data['heartRate'] = int(heart_rate_match.group(1))

    spo2_match = re.search(r'sPO2: (\d+)', data)
    if spo2_match:
        parsed_data['spo2'] = int(spo2_match.group(1))

    altitude_match = re.search(r'Altitude: (\d+)', data)
    if altitude_match:
        parsed_data['altitude'] = int(altitude_match.group(1))

    aqi_match = re.search(r'AQI: (\d+)', data)
    if aqi_match:
        if 'environment' not in parsed_data:
            parsed_data['environment'] = {}
        parsed_data['environment']['aqi'] = int(aqi_match.group(1))

    voc_match = re.search(r'VOC: ([\d.]+)', data)
    if voc_match:
        if 'environment' not in parsed_data:
            parsed_data['environment'] = {}
        parsed_data['environment']['voc'] = float(voc_match.group(1))

    amb_pressure_match = re.search(r'Ambient Pressure: ([\d.]+)', data)
    if amb_pressure_match:
        if 'environment' not in parsed_data:
            parsed_data['environment'] = {}
        parsed_data['environment']['ambientPressure'] = float(amb_pressure_match.group(1))

    humidity_match = re.search(r'Humidity: (\d+)', data)
    if humidity_match:
        parsed_data['relativeHumidity'] = int(humidity_match.group(1))

    amb_temp_match = re.search(r'Ambient temperature: (\d+)', data)
    if amb_temp_match:
        if 'environment' not in parsed_data:
            parsed_data['environment'] = {}
        parsed_data['environment']['ambientTemperature'] = int(amb_temp_match.group(1))

    battery_match = re.search(r'Battery Percentage: (\d+)', data)
    if battery_match:
        parsed_data['battery'] = int(battery_match.group(1))

    decibel_match = re.search(r'(\d+)\s+dB', data)
    if decibel_match:
        decibel = int(decibel_match.group(1))
        parsed_data['rssi'] = decibel

        if 10 < decibel < 30:
            parsed_data['textCommand'] = "Warning"
        elif 40 < decibel < 60:
            parsed_data['textCommand'] = "Alert"
        elif 70 < decibel < 90:
            parsed_data['textCommand'] = "Emergency"

    if "Emergency" in data:
        parsed_data['fallDamage'] = True

    if "YES" in data or "NO" in data or "HELP" in data or "PENDING" in data or "RESOLVED" in data:
        parsed_data['textCommand'] = data.strip()

    return parsed_data

# Function to send data to the Node.js API
async def send_data_to_nodejs(parsed_data):
    if len(parsed_data) > 1:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=parsed_data) as response:
                    print(f"Data sent to API: {parsed_data}")
                    print(f"Response: {await response.text()}")
        except Exception as e:
            print(f"Error sending data to Node.js: {e}")

# Function to fetch the latest message from the API
async def fetch_latest_message(device_id):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ALERT_API_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["success"]:
                        for message in data["mssg"]:
                            if message["jawaanId"] == "JW001" and not message["resolved"]:
                                if message["messageId"] != last_message_id[device_id]:
                                    last_message_id[device_id] = message["messageId"]
                                    return message["message"]
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

# Asynchronous function to handle reading from the device
async def handle_read(reader, device_id):
    while True:
        try:
            data = await reader.read(1024)
            if data:
                decoded_data = data.decode('utf-8').strip()
                parsed_data = parse_data(decoded_data, device_id)
                await send_data_to_nodejs(parsed_data)
        except Exception as e:
            print(f"Error reading data from {device_id}: {e}")

# Asynchronous function to handle writing to the device
async def handle_write(writer, device_id):
    while True:
        latest_message = await fetch_latest_message(device_id)
        if latest_message:
            try:
                writer.write(latest_message.encode('utf-8'))
                await writer.drain()
                print(f"Data sent to {device_id}: {latest_message}")
            except Exception as e:
                print(f"Error sending data to {device_id}: {e}")
        await asyncio.sleep(5)

# Function to manage both reading and writing for a device
async def manage_device(port, device_id):
    reader, writer = await serial_asyncio.open_serial_connection(url=port, baudrate=115200)
    read_task = asyncio.create_task(handle_read(reader, device_id))
    write_task = asyncio.create_task(handle_write(writer, device_id))

    await asyncio.gather(read_task, write_task)

# Main function to start the asyncio event loop and manage devices
async def main():
    tasks = []
    for port, device_id in zip(PORTS, DEVICE_IDS):
        tasks.append(manage_device(port, device_id))
    await asyncio.gather(*tasks)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())