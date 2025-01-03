import serial
import argparse
from datetime import datetime, timedelta

# Happy 2038! (not Y2K38 related) https://en.wikipedia.org/wiki/GPS_week_number_rollover
GPS_WEEK_ROLLOVER_N = 2

# GPS Epoch (January 6, 1980)
GPS_EPOCH = datetime(1980, 1, 6)

# GPS Week Duration (seconds in a week)
SECONDS_IN_A_WEEK = 7 * 24 * 60 * 60

def gps_to_utc(gps_week, gps_time):
    # Calculate the starting time of the GPS epoch
    week_start = GPS_EPOCH + timedelta(weeks=gps_week + 1024 * GPS_WEEK_ROLLOVER_N)
    
    # Add the number of seconds into the current week (gps_time)
    gps_datetime = week_start + timedelta(seconds=gps_time)

    return gps_datetime

def parse_message(message):
    """Parse a message and decode fields directly based on predefined specifications."""
    parsed_data = {}
    
    # Extract and decode fields
    parsed_data["Status"] = int.from_bytes(message[4:5], byteorder='big', signed=False)
    parsed_data["Lat"] = int.from_bytes(message[5:9], byteorder='big', signed=False) / 10e5
    parsed_data["Long"] = int.from_bytes(message[9:13], byteorder='big', signed=False) / 10e5
    parsed_data["alt"] = int.from_bytes(message[13:16], byteorder='big', signed=True) / 10e1
    parsed_data["d_lat"] = int.from_bytes(message[16:18], byteorder='big', signed=True) / 10e5
    parsed_data["d_long"] = int.from_bytes(message[18:20], byteorder='big', signed=True) / 10e5
    parsed_data["d_alt"] = int.from_bytes(message[20:22], byteorder='big', signed=True) / 10e2 # Doesn't seems to be right
    parsed_data["GPS_time"] = int.from_bytes(message[22:25], byteorder='big', signed=False)
    parsed_data["GPS_week"] = int.from_bytes(message[25:27], byteorder='big', signed=False)
    parsed_data["Decoded_time"] = gps_to_utc(parsed_data["GPS_week"], parsed_data["GPS_time"])
    parsed_data["SatN"] = int.from_bytes(message[27:28], byteorder='big', signed=False)
    parsed_data["S/N_signal"] = list(message[28:44])  # List of integers
    parsed_data["satellite_numbers"] = list(message[44:60])  # List of integers
    parsed_data["checksum"] = " ".join(f"{byte:02X}" for byte in message[60:62])  # Hex representation
    
    return parsed_data

def process_serial_data(data_buffer):
    """Process buffered data to extract complete messages."""
    messages = []
    start_sequence = b'\xAA\xAA\xAA'

    while True:
        start_index = data_buffer.find(start_sequence)
        if start_index == -1:
            break
        next_start_index = data_buffer.find(start_sequence, start_index + len(start_sequence))
        if next_start_index != -1:
            messages.append(data_buffer[start_index:next_start_index])
            data_buffer = data_buffer[next_start_index:]
        else:
            break

    return messages, data_buffer

def read_from_serial(port='/dev/ttyUSB0', baudrate=38400):
    buffer = b''

    try:
        with serial.Serial(port, baudrate, timeout=1) as ser:
            print(f"Listening on {port} with baud rate {baudrate}...")
            while True:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    buffer += data

                    messages, buffer = process_serial_data(buffer)

                    for message in messages:
                        parsed_data = parse_message(message)
                        hex_message = " ".join(f"{byte:02X}" for byte in message)
                        print(f"Message (raw): {hex_message}")
                        
			            # Pretty print the message
                        print(f"Message (raw): {hex_message}")
                        print("\nParsed Data:")
                        if parsed_data['Status'] == 3:
                            print(f"  Status         : Locked [3D]")
                        elif parsed_data['Status'] == 2:
                            print(f"  Status         : Locked (2D)")
                        else:
                            print(f"  Status         : Unlocked")
                        if parsed_data['Status'] >= 2: 
                            print(f"  Latitude       : {parsed_data['Lat']:.6f}°")
                            print(f"  Longitude      : {parsed_data['Long']:.6f}°")
                        else: 
                            print(f"  Latitude       : - ")
                            print(f"  Longitude      : - ")
                        if parsed_data['Status'] == 3:
                            print(f"  Altitude       : {parsed_data['alt']}m")
                        else:
                            print(f"  Altitude       : - ")
                        print(f"  Delta Latitude : {'+' if parsed_data['d_lat'] > 0 else ''}{parsed_data['d_lat']}°")
                        print(f"  Delta Longitude: {'+' if parsed_data['d_long'] > 0 else ''}{parsed_data['d_long']}°")
                        print(f"  Delta Altitude : {'+' if parsed_data['d_alt'] > 0 else ''}{parsed_data['d_alt']}m")
                        print(f"  GPS Time       : {parsed_data['GPS_time']}")
                        print(f"  GPS Week       : {parsed_data['GPS_week']}")
                        print(f"  Decoded Time   : {parsed_data['Decoded_time']}")
                        print(f"  Satellites     : {parsed_data['SatN']}")
                        print(f"  In use         : {len([x for x in parsed_data['satellite_numbers'] if x != 0])}")
                        print(f"  S/N Signal     : {' '.join(f'{x:02X}' for x in parsed_data['S/N_signal'])}")
                        print(f"  Satellite PNR  : {' '.join(f'{x:02}' for x in parsed_data['satellite_numbers'])}")
                        # print(f"  Checksum       : {parsed_data['checksum']}")
                        print("\n" + "-"*60)

    except serial.SerialException as e:
        print(f"Error opening or reading from the serial port: {e}")
    except KeyboardInterrupt:
        print("\nExiting program.")

if __name__ == "__main__":
    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Serial Port Data Reader")

    # Arguments for USB device and baudrate
    parser.add_argument('--port', type=str, default='/dev/ttyUSB0', help="USB device port (e.g., /dev/ttyUSB0 or COM3)")
    parser.add_argument('--baudrate', type=int, default=38400, help="Baud rate for the serial communication")

    # Parse arguments
    args = parser.parse_args()

    # Call the function to read from serial with the parsed arguments
    read_from_serial(port=args.port, baudrate=args.baudrate)
