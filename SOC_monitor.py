import sys
import json
import asyncio
import datetime
import pandas as pd
import keyboard
import re
import os
import logging
import threading
from bleak import BleakScanner, BleakClient, BleakError

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# Print instruction
print("Penguin SOC monitor started......\nPress Shift + 1 to save files")

# Validate MAC address format
def validate_mac(mac):
    return bool(re.match(r'^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$', mac))

# Collect information from QRs and extract mac addresses
def extract_mac():
    qr_info = input(f"Scan QR code for device({order}) from either side: ")
    try:
        data = json.loads(qr_info)
        # Check if the JSON object has the 'mac' key
        if 'mac' in data:
            mac_address = data['mac']
            formatted_mac = ':'.join([mac_address[i:i + 2] for i in range(0, len(mac_address), 2)])
            if validate_mac(formatted_mac):
                return formatted_mac
        else:
            print('MAC address not found in the QR code data, Please try again.')

    except Exception as e:
        data = f'{qr_info}'
        if validate_mac(data):
            return qr_info
        else:
            print('Invalid MAC address format, Please try again.')

    # If no valid MAC is found or an error occurs
    return extract_mac()

# Number of devices for testing
rack_id = input("\nWhat is the rack id? ")

# Number of devices for testing
try:
    num_devices = int(input("How many devices? "))
    if num_devices <= 0:
        raise ValueError("Number of devices must be a positive integer.")
except ValueError as e:
    logging.error(f"Invalid input: {e}")
    sys.exit(1)

# Store MAC addresses from user input
mac_list = []
for order in range(1, num_devices + 1):
    result = extract_mac()
    mac_list.append(result)

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
    while True:
        try:
            device = await BleakScanner.find_device_by_address(ble_address, timeout=20.0)
            if device is None:
                logging.error(f"A Bluetooth LE device with the address `{ble_address}` was not found.\n")
                return

            logging.info(f"Client found at address: {ble_address}")
            async with BleakClient(device) as client:
                battery_level, battery_sn, battery_fw = await read_battery_data(client)
                if battery_level is not None:
                    time_data = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    return battery_level, time_data, battery_sn, ble_address
                else:
                    logging.error(f"Failed to get battery data for device {ble_address}.\n")
                    return

        except Exception as e:
            logging.error(f"An unexpected error occurred with device `{ble_address}`: {e}.\n")
            return

# Dictionary to store data for each serial number
sn_data = {}

# Main execution flow
async def main():
    for mac_address in mac_list:
        result = await handle_device(mac_address)
        if result:
            battery_level, time_data, battery_sn, ble_address = result
            if battery_sn not in sn_data:
                sn_data[battery_sn] = []
            position = mac_list.index(ble_address)
            sn_data[battery_sn].append((time_data, battery_level, ble_address, position))
            logging.info(f"Battery level for device({position + 1}) {mac_address}({battery_sn}): {battery_level}% at {time_data}\n")

# Save data to individual Excel files for each SN
def save_to_excel():
    try:
        for sn, data in sn_data.items():
            timestamps_and_soc = [(timestamp, soc) for timestamp, soc, *_ in data]  # Unpack the tuples and keep timestamp and soc
            position = [item[-1] for item in data][0]
            df = pd.DataFrame(timestamps_and_soc, columns=['Timestamp', 'Battery Level'])
            file_name = f"{sn}_R{rack_id}P{position + 1}.xlsx"
            df.to_excel(file_name, index=False)
            logging.info(f"Excel file saved as {file_name}!")
    except Exception as e:
        logging.error(f"Error saving Excel files: {e}")

# Keyboard input detection in a separate thread
def listen_for_keypress():
    while True:
        if keyboard.is_pressed('!'):
            save_to_excel()
            os._exit(0)  # Exit the program

async def run_program():
    keypress_thread = threading.Thread(target=listen_for_keypress)
    keypress_thread.daemon = True
    keypress_thread.start()

    while True:
        await main()
        await asyncio.sleep(60)  # Wait for a short period before looping

if __name__ == "__main__":
        asyncio.run(run_program())

input('Enter any key to exit...')