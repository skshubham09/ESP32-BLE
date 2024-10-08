import serial
import re
import requests
import threading
import time

API_URL = "https://cms-backend-five.vercel.app/api/ble/esp"
DEVICE_IDS = ['LA10AH0001', 'LA10AH0002']  # Device IDs for the two devices
PORTS = ['COM7', 'COM10']  # Serial ports corresponding to each device
UIDS = ['JW001', 'JW002']  # Unique IDs for each device

alert_api_url = "https://cms-backend-five.vercel.app/api/alert/readAlertReply"
last_message_id = {device_id: None for device_id in DEVICE_IDS}  # Keep track of the last message ID for each device

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
        parsed_data['rssi'] = int(decibel_match.group(1))

        if 10 < parsed_data['rssi'] < 30:
            parsed_data['textCommand'] = "Warning"
        elif 40 < parsed_data['rssi'] < 60:
            parsed_data['textCommand'] = "Alert"
        elif 70 < parsed_data['rssi'] < 90:
            parsed_data['textCommand'] = "Emergency"

    if "Emergency" in data:
        parsed_data['fallDamage'] = True

    if "YES" in data or "NO" in data or "HELP" in data or "PENDING" in data or "RESOLVED" in data:
        parsed_data['textCommand'] = data.strip()

    return parsed_data

def send_data_to_nodejs(parsed_data):
    if len(parsed_data) > 2:
        try:
            response = requests.post(API_URL, json=parsed_data)
            print(f"Data sent to API: {parsed_data}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error sending data to Node.js: {e}")

def fetch_latest_message(device_id, uid):
    try:
        response = requests.get(alert_api_url)
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                for message in data["mssg"]:
                    if message["jawaanId"] == uid and not message["resolved"]:
                        if message["messageId"] != last_message_id[device_id]:
                            last_message_id[device_id] = message["messageId"]
                            return message["message"]
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

def read_from_device(port, device_id, uid):
    ser = serial.Serial(port, baudrate=115200, timeout=1)
    while True:
        try:
            data = ser.readline().decode('utf-8').strip()
            if data:
                parsed_data = parse_data(data, device_id, uid)
                send_data_to_nodejs(parsed_data)
        except Exception as e:
            print(f"Error reading data from {device_id}: {e}")

def send_data_to_device(port, device_id, uid):
    ser = serial.Serial(port, baudrate=115200, timeout=1)
    while True:
        latest_message = fetch_latest_message(device_id, uid)
        if latest_message:
            try:
                ser.write(latest_message.encode('utf-8'))
                print(f"Data sent to {device_id}: {latest_message}")
            except Exception as e:
                print(f"Error sending data to {device_id}: {e}")
        time.sleep(5)

def manage_device(port, device_id, uid):
    read_thread = threading.Thread(target=read_from_device, args=(port, device_id, uid))
    write_thread = threading.Thread(target=send_data_to_device, args=(port, device_id, uid))

    read_thread.start()
    write_thread.start()

    read_thread.join()
    write_thread.join()

if __name__ == "__main__":
    for port, device_id, uid in zip(PORTS, DEVICE_IDS, UIDS):
        threading.Thread(target=manage_device, args=(port, device_id, uid)).start()
