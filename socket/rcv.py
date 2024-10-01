import serial
import re
import requests
import json

# API endpoint to send data to
API_URL = "https://cms-backend-five.vercel.app/api/ble/esp"

# Map of COM ports to corresponding jawaan_ids
com_port_jawaan_map = {
    'COM8': '12345',  # Device connected to COM8 has jawaan_id 12345
    'COM9': '67890',  # Device connected to COM9 has jawaan_id 67890
    # Add more COM ports as necessary
}

# Set up serial connections for each COM port
ser_devices = {
    'COM8': serial.Serial('COM8', baudrate=115200, timeout=1),
    'COM9': serial.Serial('COM9', baudrate=115200, timeout=1),
    # Add more COM ports if needed
}

# Function to parse incoming data from the device
def parse_data(data):
    parsed_data = {}

    # Extract sensor values using regular expressions
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

    # Continue parsing other sensor data as needed...

    return parsed_data

# Function to send the parsed data to the API
def send_data_to_nodejs(parsed_data, jawaan_id):
    try:
        # Add jawaan_id to the data being sent
        parsed_data['jawaan_id'] = jawaan_id
        response = requests.post(API_URL, json=parsed_data)
        print(f"Data sent to API: {parsed_data}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error sending data to Node.js: {e}")

# Main function to read data from multiple COM ports and process them
def main():
    while True:
        # Iterate over all the devices connected to COM ports
        for com_port, ser in ser_devices.items():
            data = ser.readline().decode('utf-8').strip()
            
            if data:
                # Get the corresponding jawaan_id for the current COM port
                jawaan_id = com_port_jawaan_map.get(com_port)
                
                # Parse the sensor data from the device
                parsed_data = parse_data(data)
                
                # If we have valid parsed data, send it to the API
                if parsed_data and jawaan_id:
                    send_data_to_nodejs(parsed_data, jawaan_id)

if __name__ == "__main__":
    main()
