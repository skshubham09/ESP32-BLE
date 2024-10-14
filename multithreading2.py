import serial
import re
import requests
import threading
import time

# Configure the serial port and Bluetooth connection
ser = serial.Serial('COM8', baudrate=115200, timeout=1)  # Update the port as necessary
API_URL = "https://cms-backend-five.vercel.app/api/ble/esp"
DEVICE_ID = "LA10AH0001"  # Static device ID
jawaan_id = "JW001"

# API URL for fetching messages to send to the device
alert_api_url = "https://cms-backend-five.vercel.app/api/alert/readAlertReply"

# Keep track of the last sent message ID to detect new messages
last_message_id = None

# Global variables to store connection status and last device ID timestamp
last_device_id_timestamp = None
is_connected = False

# To keep track of active threads
threads = {
    'read': None,
    'write': None,
    'connection_status': None
}

stop_threads = False  # Flag to stop all threads when needed


def parse_data(data):
    global last_device_id_timestamp, is_connected
    parsed_data = {}
    parsed_data['id'] = DEVICE_ID
    parsed_data['uid'] = jawaan_id

    # Check if the device ID is in the data and update the timestamp
    if DEVICE_ID in data:
        last_device_id_timestamp = time.time()  # Update timestamp on every received ID
        if not is_connected:
            is_connected = True  # Update connection status to True when receiving valid data
            print("Device reconnected and sending valid data.")

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

    # Extract decibel value and handle noise alerts
    decibel_match = re.search(r'Noise Alert\s+(\d+\.?\d*)', data)
    if decibel_match:
        decibel = float(decibel_match.group(1))
        parsed_data['decibel'] = decibel

        if decibel > 90:
            parsed_data['noiseAlert'] = True
            send_alert_to_backend("JW001", f"Noise Alert: {decibel} dB")
        else:
            parsed_data['noiseAlert'] = False

    if "Emergency" in data:
        parsed_data['fallDamage'] = True
        send_alert_to_backend("JW001", "Emergency detected: FALLDAMAGE")
    
    if "OoR" in data:
        parsed_data['outOfRange'] = True
        send_alert_to_backend("JW001", "Out of Range!")

    if any(keyword in data for keyword in ["YES", "NO", "HELP", "PENDING", "RESOLVED", "EMERGENCY"]):
        parsed_data['textCommand'] = data.strip()
        send_alert_to_backend("JW001", data.strip())

    return parsed_data


def send_alert_to_backend(jawaan_id, message):
    alert_api_url = "https://cms-backend-five.vercel.app/api/alert/watchTosw"
    payload = {
        "jawaanId": jawaan_id,
        "message": message
    }
    try:
        response = requests.post(alert_api_url, json=payload)
        if response.status_code == 200:
            print(f"Alert sent successfully API2: {payload}")
        else:
            print(f"Failed to send alert. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error sending alert: {e}")


def send_data_to_nodejs(parsed_data):
    try:
        if len(parsed_data) > 2:
            response = requests.post(API_URL, json=parsed_data)
            print(f"Data sent to software using API_1: {parsed_data}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error sending data to Node.js: {e}")


def log_device_status(message):
    """
    Send a log message to the provided API to track connection status.
    :param message: The message describing the device status (connected or disconnected).
    """
    log_api_url = "https://cms-backend-five.vercel.app/api/log/createLogs"
    payload = {
        "id": DEVICE_ID,  # Use the DEVICE_ID as the ID
        "message": message  # Log the connection/disconnection message
    }
    try:
        response = requests.post(log_api_url, json=payload)
        if response.status_code == 200:
            print(f"Device status logged successfully: {message}")
        else:
            print(f"Failed to log device status. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error logging device status: {e}")


def check_connection_status():
    global is_connected, last_device_id_timestamp, stop_threads
    while not stop_threads:
        current_time = time.time()
        # Check if deviceId was received in the last 5 seconds
        if last_device_id_timestamp and (current_time - last_device_id_timestamp <= 5):
            if not is_connected:
                print("Device reconnected.")
                is_connected = True  # Update status when device reconnects
                start_threads()  # Restart threads on reconnection
                log_device_status("Device reconnected")  # Log the reconnection event
        else:
            if is_connected:
                print("Device disconnected.")
                is_connected = False  # Update status when device disconnects
                stop_all_threads()  # Stop threads on disconnection
                log_device_status("Device disconnected")  # Log the disconnection event

        # Prepare the data to send, including the status
        status_data = {
            "id": DEVICE_ID,
            "uid": "JW001",
            "status": is_connected
        }

        # Send the updated status to Node.js
        send_data_to_nodejs(status_data)

        # Wait for 5 seconds before checking again
        time.sleep(5)


def read_from_device():
    global stop_threads
    while not stop_threads:
        try:
            data = ser.readline().decode('utf-8').strip()
            if data:
                parsed_data = parse_data(data)
                if parsed_data:
                    send_data_to_nodejs(parsed_data)
        except Exception as e:
            print(f"Error reading data: {e}")


def send_data_to_device(data):
    try:
        ser.write(data.encode('utf-8'))
        print(f"Data sent: {data}")
        response = ser.readline().decode('utf-8').strip()
    except Exception as e:
        print(f"Error sending data: {e}")


def delete_message_by_id(message_id):
    try:
        delete_api_url = f"https://cms-backend-five.vercel.app/api/alert/readedSwToW/{message_id}"
        response = requests.put(delete_api_url)
    except Exception as e:
        print(f"Error deleting message with ID {message_id}: {e}")


def fetch_latest_message():
    global last_message_id
    try:
        response = requests.get(alert_api_url)
        if response.status_code == 200:
            data = response.json()
            if data["success"]:
                messages = data["data"]
                if messages and messages[0]["_id"] != last_message_id:
                    last_message_id = messages[0]["_id"]
                    return messages[0]["reply"]
    except Exception as e:
        print(f"Error fetching latest message: {e}")


def write_to_device_periodically():
    global stop_threads
    while not stop_threads:
        latest_message = fetch_latest_message()
        if latest_message:
            send_data_to_device(latest_message)
            delete_message_by_id(last_message_id)
        time.sleep(5)


def start_threads():
    global threads, stop_threads
    stop_threads = False

    if not threads['read'] or not threads['read'].is_alive():
        threads['read'] = threading.Thread(target=read_from_device)
        threads['read'].start()

    if not threads['write'] or not threads['write'].is_alive():
        threads['write'] = threading.Thread(target=write_to_device_periodically)
        threads['write'].start()

    if not threads['connection_status'] or not threads['connection_status'].is_alive():
        threads['connection_status'] = threading.Thread(target=check_connection_status)
        threads['connection_status'].start()


def stop_all_threads():
    global stop_threads
    stop_threads = True
    time.sleep(1)  # Ensure threads exit gracefully


# Start the threads
start_threads()
