import serial
import re
import requests
import threading
import time

# Configure the serial port and Bluetooth connection variables
COM_PORT = 'COM8'  # Update the port as necessary
BAUD_RATE = 115200
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
ser = None  # Serial connection object

# Event for thread control
restart_event = threading.Event()

def initialize_serial_connection():
    """Attempt to establish a serial connection."""
    global ser, is_connected
    while True:
        try:
            if ser and ser.is_open:
                return True  # If already connected, skip reconnection

            ser = serial.Serial(COM_PORT, baudrate=BAUD_RATE, timeout=1)
            print(f"Serial connection established on {COM_PORT}")
            is_connected = True  # Update connection status
            restart_event.clear()  # Clear the event if connected
            return True  # Return True if connection is established
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}. Retrying in 5 seconds...")
            ser = None
            is_connected = False
            restart_event.set()  # Set the event to signal threads to restart
            time.sleep(5)  # Retry every 5 seconds
            return False  # Return False if the connection failed

def parse_data(data):
    global last_device_id_timestamp
    parsed_data = {}
    parsed_data['id'] = DEVICE_ID
    parsed_data['uid'] = jawaan_id

    # Update the timestamp on every received data packet
    last_device_id_timestamp = time.time()

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
        parsed_data['rssi'] = decibel  # Assuming RSSI is decibel level

        if 10 < decibel < 30:
            parsed_data['textCommand'] = "Warning"
        elif 40 < decibel < 60:
            parsed_data['textCommand'] = "Alert"
        elif 70 < decibel < 90:
            parsed_data['textCommand'] = "Emergency"

    if "Emergency" in data:
        parsed_data['fallDamage'] = True
        send_alert_to_backend("JW001", "Emergency detected: FALLDAMAGE")

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
        if len(parsed_data) > 3:
            response = requests.post(API_URL, json=parsed_data)
            print(f"Data sent to software using API_1: {parsed_data}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error sending data to Node.js: {e}")

def check_connection_status():
    global is_connected, last_device_id_timestamp
    while True:
        current_time = time.time()
        # Check if data was received in the last 5 seconds
        if last_device_id_timestamp and (current_time - last_device_id_timestamp <= 5):
            if not is_connected:
                print("Device reconnected.")
                is_connected = True  # Update status when device reconnects
                restart_event.clear()  # Clear the event
        else:
            if is_connected:
                print("Device disconnected.")
                is_connected = False  # Update status when device disconnects
                restart_event.set()  # Set the event to signal threads to restart

        # Prepare the data to send, including the status
        status_data = {
            "id": DEVICE_ID,
            "uid": jawaan_id,
            "status": is_connected
        }

        # Send the updated status to Node.js
        send_data_to_nodejs(status_data)

        # Wait for 5 seconds before checking again
        time.sleep(5)

def reconnect_serial():
    """Handle the reconnection process."""
    global ser, is_connected
    try:
        if ser and ser.is_open:
            ser.close()
        print("Reconnecting serial connection...")
        initialize_serial_connection()
        is_connected = True  # Update connection status after reconnection
    except Exception as e:
        print(f"Error during reconnection: {e}")
        is_connected = False

def read_from_device():
    global ser
    while True:
        if ser is None or not ser.is_open:
            reconnect_serial()
            continue  # Retry connection before attempting to read data

        try:
            data = ser.readline().decode('utf-8').strip()
            if data:
                parsed_data = parse_data(data)
                if parsed_data:
                    send_data_to_nodejs(parsed_data)
        except serial.SerialException as e:
            print(f"Serial port error: {e}. Reconnecting...")
            reconnect_serial()
        except Exception as e:
            print(f"Error reading data: {e}")

        # Check if the restart event is set
        if restart_event.is_set():
            print("Restarting read thread...")
            break  # Exit to restart the thread

def send_data_to_device(data):
    global ser
    try:
        if ser is None or not ser.is_open:
            reconnect_serial()  # Reconnect if serial connection is lost
        ser.write(data.encode('utf-8'))
        print(f"Data sent: {data}")
        response = ser.readline().decode('utf-8').strip()
    except serial.SerialException as e:
        print(f"Error sending data: {e}. Reconnecting...")
        reconnect_serial()
    except Exception as e:
        print(f"Error sending data: {e}")

def delete_message_by_id(message_id):
    try:
        # Construct the delete API URL with the message ID
        delete_api_url = f"https://cms-backend-five.vercel.app/api/alert/deleteAlert/{message_id}"
        response = requests.delete(delete_api_url)
        if response.status_code == 200:
            print(f"Message with ID {message_id} deleted successfully.")
        else:
            print(f"Failed to delete message with ID {message_id}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error deleting message: {e}")

def fetch_latest_message():
    global last_message_id
    try:
        response = requests.get(alert_api_url)
        if response.status_code == 200:
            messages = response.json()
            if messages:
                latest_message = messages[-1]  # Get the latest message
                if latest_message['id'] != last_message_id:  # Check if it's new
                    last_message_id = latest_message['id']  # Update last message ID
                    return latest_message['message']
        else:
            print(f"Failed to fetch latest message. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching latest message: {e}")
    return None

def write_to_device():
    global last_message_id
    while True:
        latest_message = fetch_latest_message()

        # If there's a new message, send it to the device
        if latest_message:
            send_data_to_device(latest_message)
            if last_message_id:
                delete_message_by_id(last_message_id)

        # Wait for a few seconds before checking again
        time.sleep(5)

        # Check if the restart event is set
        if restart_event.is_set():
            print("Restarting write thread...")
            break  # Exit to restart the thread

if __name__ == "__main__":
    # Initialize the serial connection
    initialize_serial_connection()

    # Create threads for reading data, writing data, and checking connection status
    while True:  # Main loop to restart threads as needed
        read_thread = threading.Thread(target=read_from_device)
        write_thread = threading.Thread(target=write_to_device)
        connection_status_thread = threading.Thread(target=check_connection_status)

        read_thread.start()
        write_thread.start()
        connection_status_thread.start()

        read_thread.join()
        write_thread.join()
        connection_status_thread.join()

        # Check if the restart event is set, which means we need to restart the threads
        if restart_event.is_set():
            print("Restarting all threads due to connection status change.")
            restart_event.clear()  # Clear the event for the next loop
