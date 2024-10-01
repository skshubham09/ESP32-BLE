import serial
import re
import requests
import json

# Configure the serial port and Bluetooth connection
ser = serial.Serial('COM8', baudrate=115200, timeout=1)  # Update the port as necessary

API_URL = "https://cms-backend-five.vercel.app/api/ble/esp"
# DEVICE_ID = "LA10AH0001"  # Static device ID

def parse_data(data):
    parsed_data = {}

    # Add device ID to the data
    # parsed_data['Device ID'] = DEVICE_ID
    temp_match = re.search(r'Device_id: (\w+)', data)
    if temp_match:
        parsed_data['Device_id'] = int(temp_match.group(1))
    # Extract values using regular expressions
    temp_match = re.search(r'Body temperature: (\d+)', data)
    if temp_match:
        parsed_data['Body temperature'] = int(temp_match.group(1))

    resp_match = re.search(r'Respiration rate: (\d+)', data)
    if resp_match:
        parsed_data['Respiration rate'] = int(resp_match.group(1))

    heart_rate_match = re.search(r'Heart Rate: (\d+)', data)
    if heart_rate_match:
        parsed_data['Heart Rate'] = int(heart_rate_match.group(1))

    spo2_match = re.search(r'sPO2: (\d+)', data)
    if spo2_match:
        parsed_data['sPO2'] = int(spo2_match.group(1))

    altitude_match = re.search(r'Altitude: (\d+)', data)
    if altitude_match:
        parsed_data['Altitude'] = int(altitude_match.group(1))

    aqi_match = re.search(r'AQI: (\d+)', data)
    if aqi_match:
        parsed_data['AQI'] = int(aqi_match.group(1))

    voc_match = re.search(r'VOC: ([\d.]+)', data)
    if voc_match:
        parsed_data['VOC'] = float(voc_match.group(1))

    amb_pressure_match = re.search(r'Ambiet Pressure: ([\d.]+)', data)
    if amb_pressure_match:
        parsed_data['Ambient Pressure'] = float(amb_pressure_match.group(1))

    humidity_match = re.search(r'Humidity: (\d+)', data)
    if humidity_match:
        parsed_data['Humidity'] = int(humidity_match.group(1))

    amb_temp_match = re.search(r'Ambient temperature: (\d+)', data)
    if amb_temp_match:
        parsed_data['Ambient temperature'] = int(amb_temp_match.group(1))

    battery_match = re.search(r'Battery Percentage: (\d+)', data)
    if battery_match:
        parsed_data['Battery Percentage'] = int(battery_match.group(1))

    # Decibel warnings
    decibel_match = re.search(r'(\d+)\s+dB', data)
    if decibel_match:
        decibel = int(decibel_match.group(1))
        parsed_data['Decibel'] = decibel

        if 10 < decibel < 30:
            parsed_data['Alert Level'] = "Warning"
        elif 40 < decibel < 60:
            parsed_data['Alert Level'] = "Alert"
        elif 70 < decibel < 90:
            parsed_data['Alert Level'] = "Emergency"

    # Fall detection
    if "Emergency" in data:
        parsed_data['Fall Detected'] = True

    # Command responses from the ESP32
    if "YES" in data or "NO" in data or "HELP" in data or "PENDING" in data or "RESOLVED" in data:
        parsed_data['Command Response'] = data.strip()

    # Return the parsed data
    return parsed_data

def send_data_to_nodejs(parsed_data):
    # Remove 'Device ID' from the check to ensure that sensor data is present
    sensor_data = {k: v for k, v in parsed_data.items() if k != 'Device ID'}

    # Only send data if sensor data (like temperature, heart rate, etc.) is present
    if sensor_data:
        try:
            response = requests.post(API_URL, json=parsed_data)
            print(f"Data sent to API: {parsed_data}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Data sent to API: {parsed_data}")
            print(f"Error sending data to Node.js: {e}")
    
        

def main():
    while True:
        # Read and decode a line of data from the serial port
        data = ser.readline().decode('utf-8').strip()
        
        if data:
            # Parse the data
            parsed_data = parse_data(data)
            
            # If we have valid parsed data, send it to the API
            if parsed_data:
                send_data_to_nodejs(parsed_data)

if __name__ == "__main__":
    main()
