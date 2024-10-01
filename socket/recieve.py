import serial
import re
import requests
import json

# Configure the serial port and Bluetooth connection
ser = serial.Serial('COM8', baudrate=115200, timeout=1)  # Update the port as necessary

API_URL = "https://cms-backend-five.vercel.app/api/ble/esp"
JAWAAN_ID = "12345"  # Set the specific jawaan ID here

def parse_data(data):
    parsed_data = {}

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

    # Return the parsed data
    return parsed_data

def send_data_to_nodejs(parsed_data, jawaan_id):
    try:
        # Add jawaan_id to the data being sent
        parsed_data['jawaan_id'] = jawaan_id  

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
                send_data_to_nodejs(parsed_data, JAWAAN_ID)

if __name__ == "__main__":
    main()
