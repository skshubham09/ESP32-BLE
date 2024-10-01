import serial

# Configure the serial port and Bluetooth connection
ser = serial.Serial('COM7', baudrate=115200, timeout=1)  # Update the port as necessary

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

def main():
    while True:
        # Get input from the user
        data_to_send = input("Enter data to send to the device (type 'exit' to quit): ")
        
        # If user types 'exit', terminate the program
        if data_to_send.lower() == 'exit':
            print("Exiting program.")
            break
        
        # Send the data to the device
        send_data_to_device(data_to_send)

if __name__ == "__main__":
    main()
