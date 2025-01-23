import sys
import json
import asyncio
import datetime
import numpy as np
import keyboard
from bleak import BleakScanner, BleakClient, BleakError
import re
import logging
import threading

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# Validate MAC address format
def validate_mac(mac):
    return bool(re.match(r'^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$', mac))

# Extract MAC address from QR code information
def extract_mac(qr_info):
    try:
        mac_address = json.loads(qr_info[0])['mac']
        formatted_mac = ':'.join([mac_address[i:i + 2] for i in range(0, len(mac_address), 2)])
        return formatted_mac
    except Exception as e:
        for element in qr_info:
            if len(element) == 17:  # Standard MAC address length
                return element
        return 'Invalid MAC address'

# Number of devices for testing
num_devices = int(input("How many devices? "))

# Store MAC addresses from user input
mac_list = []
for i in range(1, len(sys.argv)):
    mac_list.append(sys.argv[i])

if not mac_list:
    for i in range(1, num_devices + 1):
        qr_info = [input(f'Scan either QR for device {i}:')]
        mac_list.append(extract_mac(qr_info))

# UUIDs for battery GATT server
BATTERY_LEVEL_UUID = "00002A19-0000-1000-8000-00805F9B34FB"
BATTERY_SN_UUID = "00002A25-0000-1000-8000-00805F9B34FB"
BATTERY_FW_UUID = "00002A26-0000-1000-8000-00805F9B34FB"

# Read battery level from device
async def read_battery_data(client):
    try:
        battery_level = await client.read_gatt_char(BATTERY_LEVEL_UUID)
        battery_sn = await client.read_gatt_char(BATTERY_SN_UUID)
        battery_fw = await client.read_gatt_char(BATTERY_FW_UUID)
        return battery_level[0], battery_sn.decode('utf-8'), battery_fw.decode('utf-8')
    except BleakError as e:
        logging.error(f"Error reading battery data: {e}")
        return None

# Handle BLE device connection and reading
async def handle_device(ble_address):
    max_retries = 2  # Number of times to retry connection on failure
    attempt = 0  # Track the number of attempts

    while attempt <= max_retries:
        try:
            if not validate_mac(ble_address):
                logging.error(f"Invalid MAC address format detected: {ble_address}")
                return
            device = await BleakScanner.find_device_by_address(ble_address, timeout=20.0)
            if device is None:
                logging.error(f"A Bluetooth LE device with the address `{ble_address}` was not found.")
                return

            logging.info(f"Client found at address: {ble_address}")
            async with BleakClient(device) as client:
                battery_level, battery_sn, battery_fw = await read_battery_data(client)
                if battery_level is not None:
                    time_data = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    return battery_level, time_data, battery_fw, battery_sn
                else:
                    logging.error(f"Failed to get battery data for device {ble_address}")
                    return

        except (BleakError, TimeoutError) as e:
            logging.error(f"Error while interacting with BLE device at `{ble_address}`: {e}")
            return

        except Exception as e:
            logging.error(f"An unexpected error occurred with device `{ble_address}`: {e}")
            return

soc_data = []
# Main execution flow
async def main():
    for ble_address in mac_list:
        result = await handle_device(ble_address)
        if result:
            battery_level, time_data, battery_fw, battery_sn = result
            soc_data.append([battery_sn, battery_fw, ble_address, battery_level, time_data])
            logging.info(f"Battery level for device {ble_address}({battery_sn}): {battery_level}% at {time_data}")

# Keyboard input detection in a separate thread
def listen_for_keypress():
    while True:
        if keyboard.is_pressed('x'):  # Detect if 'x' is pressed
            np.savetxt(f'penguin_{datetime.date.today()}.csv', soc_data, fmt='%s', delimiter=',')
            print('CSV file saved!')
            exit()  # Exit the program

async def run_program():
    # Start the key press listener in a separate thread
    keypress_thread = threading.Thread(target=listen_for_keypress)
    keypress_thread.daemon = True  # Allow thread to exit when the main program exits
    keypress_thread.start()

    while True:
        await main()

        await asyncio.sleep(120)  # Wait for a short period before checking again

if __name__ == "__main__":
    asyncio.run(run_program())

input('Press enter to exit')
