import serial
import requests
import time

# Configure the serial port and Bluetooth connection
ser = serial.Serial('COM7', baudrate=115200, timeout=1)  # Update the port as necessary

# URL of the API
api_url = "https://cms-backend-five.vercel.app/api/alert/readAlertReply"

# Keep track of the last sent message ID to detect new messages
last_message_id = None

def send_data_to_device(data):
    try:
        # Send data to the device over serial
        ser.write(data.encode('utf-8'))
        print(f"Data sent: {data}")

        # Check for a response from the device
        response = ser.readline().decode('utf-8').strip()  # Read the response from the device
        if response:
            print(f"Response from device: {response}")
        else:
            print("No response from device.")
    except Exception as e:
        print(f"Error sending data: {e}")

def fetch_latest_message():
    global last_message_id

    try:
        # Perform a GET request to fetch the data from the API
        response = requests.get(api_url)
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

def main():
    while True:
        # Fetch the latest message for JW001
        latest_message = fetch_latest_message()

        # If there's a new message, send it to the device
        if latest_message:
            send_data_to_device(latest_message)

        # Wait for a few seconds before checking again
        time.sleep(5)

if __name__ == "__main__":
    main()
