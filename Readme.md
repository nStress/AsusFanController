# Fan Control and Monitoring Application

This Python application allows you to control and monitor the fans and temperature of your laptop or PC, specifically designed to work with ASUS devices using the `AsusWinIO64.dll` library. The application provides real-time monitoring of CPU and GPU temperatures, fan speeds, and allows you to adjust fan speeds based on temperature. Additionally, the app offers a fan testing feature to evaluate the performance and synchronization of the fans.

## Features

- **Monitor CPU and GPU Temperatures**: Displays real-time CPU and GPU temperatures.
- **Monitor Fan Speeds**: Shows the RPM of the CPU and GPU fans.
- **Adjust Fan Speed**: Automatically adjusts fan speeds based on CPU and GPU temperature.
- **Test Fans**: Run a test to evaluate the health of the fans and their synchronization.
- **Log Data**: Optionally log CPU and fan data to the console for analysis.
- **Graphical User Interface (GUI)**: A simple and intuitive interface built with Tkinter.

## Installation

To use this application, you need the following dependencies:

- Python 3.x
- `cffi` library for interacting with the ASUS fan control DLL
- `psutil` for reading CPU temperature
- `GPUtil` for reading GPU temperature
- `tkinter` for the graphical interface

### Install dependencies:

'''
pip install cffi psutil GPUtil tkinter
'''

Ensure you have the **`AsusWinIO64.dll`** file in the same directory as this script or specify the path in the code.

## Usage

1. **Running the Application**:
    - Simply run the `fan_control.py` script using Python.
    - The application window will appear with the current temperatures for CPU and GPU and the fan speeds.
    - You can adjust the fan speeds using the slider or let the app adjust them automatically based on temperature.

2. **Main Controls**:
    - **Adjust Fan Speed**: The fan speeds can be adjusted manually using the slider or automatically based on CPU/GPU temperatures.
    - **Test Fans**: Run a fan speed test that gradually increases fan speeds and evaluates their health and synchronization.
    - **Log Data**: Enable logging from the options menu to monitor and log CPU and fan data in the console.

3. **Exit the Application**:
    - Click the close button to shut down the application and stop monitoring the fans.

### Fan Testing:

The fan test will:
- Gradually increase the fan speeds.
- Log the average fan speeds and health.
- Determine the synchronization between the CPU and GPU fans.
- Provide feedback on whether the fans are performing optimally or need attention.

### Synchronization:

If you choose to test fan synchronization, the application ensures that the CPU and GPU fans are running at similar speeds for optimal cooling. If they are too far apart, the application will attempt to synchronize their speeds.

## Code Explanation

### Core Classes and Functions

- **`AsusControl`**: A class that interfaces with the `AsusWinIO64.dll` to interact with the hardware, set fan speeds, and fetch CPU/GPU temperatures.
    - `set_fan_speed(value, fan_index=0)`: Sets the speed of a specific fan.
    - `set_all_fans_speed(percentage)`: Sets the speed of all fans to a percentage value.
    - `reset_fans()`: Resets fan settings.
    - `get_fan_count()`: Returns the number of fans.
    - `get_fan_speed(fan_index)`: Returns the speed (RPM) of a specific fan.
    - `get_cpu_temperature()`: Returns the CPU temperature in °C.
    - `get_gpu_temperature()`: Returns the GPU temperature in °C.

- **`monitor_fans(asus_control, cpu_temp_text, gpu_temp_text, fan1_text, fan2_text)`**: Continuously monitors and updates CPU/GPU temperatures and fan speeds in the GUI.

- **`adjust_fan_speed_by_temp()`**: Adjusts fan speeds automatically based on CPU and GPU temperatures to keep them within a safe range.

- **`run_test(progress_bar, progress_label)`**: Runs a fan speed test and provides feedback on fan health and synchronization.

- **`update_progress_bar(value, max_value, progress_bar, progress_label)`**: Updates the progress bar during the fan test.

- **`calculate_fan_health(speed, fan_name)`**: Evaluates the health of a fan based on its speed (RPM).

- **`test_fan()`**: Initializes the GUI and starts the fan test in a separate thread.

## Troubleshooting

- **Error: "Failed to initialize WinIO"**: Ensure that the `AsusWinIO64.dll` file is present in the same directory as this script.
- **Error: "Could not fetch CPU temperature"**: This may occur if your system doesn't support reading the CPU temperature via the available method. Ensure `psutil` is installed and your system supports temperature monitoring.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Feel free to fork the repository and create pull requests for bug fixes or new features. Please make sure to follow the coding standards and write tests for any new functionality.
'''


