import serial
import re
import requests
import threading
import time

# API and device configuration
API_URL = "https://cms-backend-five.vercel.app/api/ble/esp"
DEVICE_IDS = ['LA10AH0001', 'LA10AH0002']  # Device IDs for the two devices
PORTS = ['COM7', 'COM10']  # Serial ports corresponding to each device
UIDS = ['JW001', 'JW002']  # Unique IDs for each device

# API URL for fetching messages to send to the devices
alert_api_url = "https://cms-backend-five.vercel.app/api/alert/readAlertReply"
last_message_id = {device_id: None for device_id in DEVICE_IDS}  # Track last message ID for each device

# Dictionary to hold serial connections for each device
serial_connections = {device_id: None for device_id in DEVICE_IDS}

# Initialize serial connections for each device
def initialize_serial_connections():
    for idx, port in enumerate(PORTS):
        try:
            ser = serial.Serial(port, baudrate=115200, timeout=1)
            serial_connections[DEVICE_IDS[idx]] = ser
            print(f"Initialized serial connection for {DEVICE_IDS[idx]} on port {port}")
        except Exception as e:
            print(f"Error initializing serial connection on {port}: {e}")

# Parse data for each device based on the device ID and UID
def parse_data(data, device_id, uid):
    parsed_data = {'id': device_id, 'uid': uid}
    
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

    amb_pressure_match = re.search(r'Ambiet Pressure: ([\d.]+)', data)
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
        parsed_data['rssi'] = decibel  # Assuming RSSI is decibel level

        if 10 < decibel < 30:
            parsed_data['textCommand'] = "Warning"
        elif 40 < decibel < 60:
            parsed_data['textCommand'] = "Alert"
        elif 70 < decibel < 90:
            parsed_data['textCommand'] = "Emergency"

    if "Emergency" in data:
        parsed_data['fallDamage'] = True
        send_alert_to_backend(uid, "Emergency detected")

    if any(x in data for x in ["YES", "NO", "HELP", "PENDING", "RESOLVED"]):
        parsed_data['textCommand'] = data.strip()
        send_alert_to_backend(uid, data.strip())

    return parsed_data

# Send alert to the backend
def send_alert_to_backend(jawaan_id, message):
    alert_api_url = "https://cms-backend-five.vercel.app/api/alert/watchTosw"
    payload = {
        "jawaanId": jawaan_id,
        "message": message
    }
    try:
        response = requests.post(alert_api_url, json=payload)
        if response.status_code == 200:
            print(f"Alert sent successfully: {payload}")
        else:
            print(f"Failed to send alert. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error sending alert: {e}")

# Send parsed data to Node.js backend
def send_data_to_nodejs(parsed_data):
    try:
        if len(parsed_data) > 2:
            response = requests.post(API_URL, json=parsed_data)
            print(f"Data sent to API: {parsed_data}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error sending data to Node.js: {e}")

# Function to read from the serial device
def read_from_device(device_id, uid):
    ser = serial_connections[device_id]
    while True:
        try:
            data = ser.readline().decode('utf-8').strip()
            if data:
                parsed_data = parse_data(data, device_id, uid)
                if parsed_data:
                    send_data_to_nodejs(parsed_data)
        except Exception as e:
            print(f"Error reading data from {device_id}: {e}")

# Function to send data to the device
def send_data_to_device(device_id, data):
    ser = serial_connections[device_id]
    try:
        ser.write(data.encode('utf-8'))
        print(f"Data sent to {device_id}: {data}")
        response = ser.readline().decode('utf-8').strip()

        if response:
            print(f"Response from {device_id}: {response}")
        else:
            print(f"No response from {device_id}.")
    except Exception as e:
        print(f"Error sending data to {device_id}: {e}")

# Function to fetch the latest message for a given UID
def fetch_latest_message(uid):
    global last_message_id

    try:
        response = requests.get(alert_api_url)
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                for message in data["mssg"]:
                    if message["jawaanId"] == uid and not message["resolved"]:
                        if message["messageId"] != last_message_id[uid]:
                            last_message_id[uid] = message["messageId"]
                            return message["message"]
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

# Function to delete the message by ID
def delete_message_by_id(message_id, uid):
    try:
        delete_api_url = f"https://cms-backend-five.vercel.app/api/alert/readedSwToW/{message_id}"
        response = requests.put(delete_api_url)
    except Exception as e:
        print(f"Error deleting message for {uid}: {e}")

# Function to write data to the device
def write_to_device(device_id, uid):
    global last_message_id
    while True:
        latest_message = fetch_latest_message(uid)
        if latest_message:
            send_data_to_device(device_id, latest_message)
            if last_message_id[uid]:
                delete_message_by_id(last_message_id[uid], uid)
        time.sleep(5)

if __name__ == "__main__":
    # Initialize serial connections
    initialize_serial_connections()

    # Create separate threads for reading and writing for each device
    threads = []
    for i, device_id in enumerate(DEVICE_IDS):
        read_thread = threading.Thread(target=read_from_device, args=(device_id, UIDS[i]))
        write_thread = threading.Thread(target=write_to_device, args=(device_id, UIDS[i]))
        threads.extend([read_thread, write_thread])

    # Start all threads
    for thread in threads:
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()