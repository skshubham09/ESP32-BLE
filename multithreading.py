import serial
import re
import requests
import threading
import time

# Configure the serial port and Bluetooth connection
ser = serial.Serial('COM7', baudrate=115200, timeout=1)  # Update the port as necessary
API_URL = "https://cms-backend-five.vercel.app/api/ble/esp"
DEVICE_ID = "LA10AH0001"  # Static device ID

# API URL for fetching messages to send to the device
alert_api_url = "https://cms-backend-five.vercel.app/api/alert/readAlertReply"

# Keep track of the last sent message ID to detect new messages
last_message_id = None

def parse_data(data):
    parsed_data = {}
    parsed_data['id'] = DEVICE_ID
    parsed_data['uid'] = "JW001" 
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
        send_alert_to_backend("JW001", "Emergency detected")

    if "YES" in data or "NO" in data or "HELP" in data or "PENDING" in data or "RESOLVED" in data:
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
            print(f"Alert sent successfully: {payload}")
        else:
            print(f"Failed to send alert. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error sending alert: {e}")


def send_data_to_nodejs(parsed_data):
    try:
        if len(parsed_data) > 2:
            response = requests.post(API_URL, json=parsed_data)
            print(f"Data sent to API: {parsed_data}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error sending data to Node.js: {e}")

def read_from_device():
    while True:
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
        
        if response:
            print(f"Response from device: {response}")
        else:
            print("No response from device.")
    except Exception as e:
        print(f"Error sending data: {e}")

def delete_message_by_id(message_id):
    try:
        # Construct the delete API URL with the message ID
        delete_api_url = f"https://cms-backend-five.vercel.app/api/alert/readedSwToW/{message_id}"
        
        # # Perform a GET request to delete the message by its ID
        response = requests.put(delete_api_url)
        # print(response)
        # # Check if the request was successful
        # if response.status_code == 200:
        #     print(f"Message with ID {message_id} deleted successfully.")
        # else:
        #     print(f"Failed to delete message with ID {message_id}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error deleting message with ID {message_id}: {e}")

def fetch_latest_message():
    global last_message_id

    try:
        # Perform a GET request to fetch the data from the API
        response = requests.get(alert_api_url)
        if response.status_code == 200:
            data = response.json()

            # Check if the API call was successful
            if data["success"]:
                for message in data["mssg"]:
                    if message["jawaanId"] == "JW001" and not message["resolved"]:
                        # Check if the message is new by comparing the messageId
                        if message["messageId"] != last_message_id:
                            last_message_id = message["messageId"]
                            return message["message"]
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching data: {e}")

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

if __name__ == "__main__":
    # Create two threads: one for reading and one for writing
    read_thread = threading.Thread(target=read_from_device)
    write_thread = threading.Thread(target=write_to_device)

    # Start both threads
    read_thread.start()
    write_thread.start()

    # Wait for both threads to complete
    read_thread.join()
    write_thread.join()
