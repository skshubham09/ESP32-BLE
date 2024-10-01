import serial
import re
import requests
import json
import threading

# Configure the serial port and Bluetooth connection
ser = serial.Serial('COM7', baudrate=115200, timeout=1)  # Update the port as necessary
API_URL = "https://cms-backend-five.vercel.app/api/ble/esp"
DEVICE_ID = "LA10AH0001"  # Static device ID

def parse_data(data):
    parsed_data = {}
    parsed_data['id'] = DEVICE_ID

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

    if "YES" in data or "NO" in data or "HELP" in data or "PENDING" in data or "RESOLVED" in data:
        parsed_data['textCommand'] = data.strip()

    return parsed_data

def send_data_to_nodejs(parsed_data):
    try:
        if len(parsed_data) > 1:
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

def write_to_device():
    while True:
        data_to_send = input("Enter data to send to the device (type 'exit' to quit): ")
        if data_to_send.lower() == 'exit':
            print("Exiting program.")
            break
        send_data_to_device(data_to_send)

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