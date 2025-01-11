import sys
import json
import asyncio
import datetime
import numpy as np
from bleak import BleakScanner, BleakClient, BleakError
import re
import logging

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
BATTERY_SERVICE_UUID = "0000180F-0000-1000-8000-00805F9B34FB"
BATTERY_LEVEL_UUID = "00002A19-0000-1000-8000-00805F9B34FB"

# Read battery level from device
async def read_battery_data(client):
    try:
        battery_level = await client.read_gatt_char(BATTERY_LEVEL_UUID)
        return battery_level[0]  # Return the battery level
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
                battery_level = await read_battery_data(client)
                if battery_level is not None:
                    time_data = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    return battery_level, time_data
                else:
                    logging.error(f"Failed to get battery data for device {ble_address}")
                    return

        except (BleakError, TimeoutError) as e:
            logging.error(f"Error while interacting with BLE device at `{ble_address}`: {e}")
            attempt += 1
            if attempt <= max_retries:
                logging.info(f"Attempt {attempt} failed. Retrying...")
                await asyncio.sleep(2)  # Sleep for a short period before retrying
            else:
                logging.error(f"Failed to connect to `{ble_address}` after {max_retries + 1} attempts.")
            return

        except Exception as e:
            logging.error(f"An unexpected error occurred with device `{ble_address}`: {e}")
            return

# Main execution flow
async def main():
    soc_data = []
    for ble_address in mac_list:
        result = await handle_device(ble_address)
        if result:
            battery_level, time_data = result
            soc_data.append([ble_address, battery_level, time_data])
            logging.info(f"Battery level for device {ble_address}: {battery_level}% at {time_data}")

    np.savetxt(f'penguin{datetime.date.today()}.csv', soc_data, fmt='%s', delimiter=',')

if __name__ == "__main__":
    asyncio.run(main())
