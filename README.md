# ble-battery-soc-monitor
A Python script to monitor the battery levels of backup power units using their onboard Bluetooth. It connects to devices, retrieves battery data, and logs the results into a CSV file for future analysis.

## Features
- Validates and extracts MAC addresses from QR code information.
- Reads battery levels using BLE GATT services.
- Handles connection retries and errors.
- Saves battery data with timestamps into a CSV file.
