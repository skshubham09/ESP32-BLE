import serial
import re
import requests
import json
import time

# Configure the serial port and Bluetooth connection
# Update 'COM3' with the appropriate virtual COM port assigned to your Bluetooth device
SERIAL_PORT = 'COM4'
BAUD_RATE = 115200
TIMEOUT = 1

API_URL = "https://cms-backend-five.vercel.app/api/ble/esp"

def open_serial_connection():
    """
    Attempt to open the serial connection to the Bluetooth device.
    """
    try:
        ser = serial.Serial(SERIAL_PORT, baudrate=BAUD_RATE, timeout=TIMEOUT)
        print(f"Connected to Bluetooth device on {SERIAL_PORT}")
        return ser
    except serial.SerialException as e:
        print(f"Failed to connect to {SERIAL_PORT}: {e}")
        return None

def parse_data(data):
    """
    Parse incoming Bluetooth data and extract sensor values using regular expressions.
    """
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

    return parsed_data

def send_data_to_nodejs(parsed_data):
    """
    Send parsed data to the specified Node.js backend API.
    """
    try:
        response = requests.post(API_URL, json=parsed_data)
        print(f"Data sent to API: {parsed_data}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error sending data to API: {e}")

def main():
    """
    Main function that handles Bluetooth communication and data parsing.
    """
    ser = open_serial_connection()

    # Ensure the serial connection is successfully opened
    if ser is None:
        return

    try:
        while True:
            # Read and decode a line of data from the serial port
            data = ser.readline().decode('utf-8').strip()

            if data:
                print(f"Received: {data}")  # Optional: Log received data
                parsed_data = parse_data(data)

                # If valid data is parsed, send it to the API
                if parsed_data:
                    send_data_to_nodejs(parsed_data)

            time.sleep(0.1)  # Add a short delay to avoid overwhelming the serial port
    except serial.SerialException as e:
        print(f"Serial communication error: {e}")
    except KeyboardInterrupt:
        print("Program interrupted by user.")
    finally:
        # Always close the serial connection when done
        if ser:
            ser.close()
            print("Serial connection closed.")

if __name__ == "__main__":
    main()
