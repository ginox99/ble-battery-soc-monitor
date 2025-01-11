# ble-battery-soc-monitor
A Python script to monitor the battery levels of backup power units using their onboard Bluetooth. It connects to devices, retrieves battery data, and logs the results into a CSV file for future analysis.

## Features
- Validates and extracts MAC addresses from QR code information.
- Reads battery levels using BLE GATT services.
- Handles connection retries and errors.
- Saves battery data with timestamps into a CSV file.

## TODO
- [ ] Improve error handling for invalid QR codes.
- [ ] Add Charging State: Detect if the device is charging (SoC increasing), discharging (SoC decreasing), or full (SoC stable).
- [ ] Implement an option to specify custom output directories for CSV files.
- [ ] Support additional GATT characteristics, such as device temperature.
- [ ] Build a simple GUI for user-friendly input of MAC addresses.
