import cffi
import threading
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import psutil
import GPUtil
import traceback
import math

# --- Constants ---

# Fan Speed & Temperature
MAX_FAN_SPEED = 5000
TARGET_TEMP = 60
MIN_FAN_SPEED_PERCENTAGE = 50
MAX_FAN_SPEED_PERCENTAGE = 100
TEMP_CHANGE_THRESHOLD = 2
MONITORING_INTERVAL = 1  # seconds

# Fan Health Test
POOR_FAN_RPM = 2000
GOOD_FAN_RPM = 3500
EXCELLENT_FAN_RPM = 4500
SYNC_RPM_THRESHOLD = 500
TEST_RAMP_UP_STEP = 5
TEST_RAMP_UP_DELAY = 1  # seconds
TEST_READING_COUNT = 20
TEST_READING_DELAY = 1  # seconds

# GUI Dimensions & Colors
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 450
BG_COLOR = "#1e1e2f"
FRAME_COLOR = "#2e3440"
OUTLINE_COLOR = "#4c566a"
TEXT_COLOR = "white"
ACCENT_COLOR = "#88c0d0"
SLIDER_COLOR = "#2980b9"
BUTTON_COLOR = "#5865F2"
BUTTON_ACTIVE_COLOR = "#4752C4"

SLIDER_START_X = 100
SLIDER_END_X = 500
SLIDER_Y = 320
SLIDER_MARKER_RADIUS = 10

ffi = cffi.FFI()

ffi.cdef("""
    int InitializeWinIo();
    void ShutdownWinIo();
    void HealthyTable_SetFanIndex(char fanIndex);
    void HealthyTable_SetFanTestMode(char mode);
    void HealthyTable_SetFanPwmDuty(char pwmDuty);
    int HealthyTable_FanCounts();
    int HealthyTable_FanRPM();
    int Thermal_Read_Cpu_Temperature();
""")

fan_control_lib = ffi.dlopen("AsusWinIO64.dll")

class AsusControl:
    def __init__(self):
        if fan_control_lib.InitializeWinIo() == 0:
            raise Exception("Failed to initialize WinIO.")

    def __del__(self):
        fan_control_lib.ShutdownWinIo()

    def set_fan_speed(self, value, fan_index=0):
        fan_control_lib.HealthyTable_SetFanIndex(ffi.cast("char", fan_index))
        fan_control_lib.HealthyTable_SetFanTestMode(ffi.cast("char", 1))  # Test mode
        fan_control_lib.HealthyTable_SetFanPwmDuty(ffi.cast("char", value))

    def set_all_fans_speed(self, percentage):
        fan_count = fan_control_lib.HealthyTable_FanCounts()
        pwm_value = int(percentage * 255 / 100)
        for fan_index in range(fan_count):
            self.set_fan_speed(pwm_value, fan_index)

    def reset_fans(self):
        fan_count = fan_control_lib.HealthyTable_FanCounts()
        for fan_index in range(fan_count):
            fan_control_lib.HealthyTable_SetFanTestMode(ffi.cast("char", 0))  # Reset fan test mode

    def get_fan_count(self):
        return fan_control_lib.HealthyTable_FanCounts()

    def get_fan_speed(self, fan_index):
        fan_control_lib.HealthyTable_SetFanIndex(ffi.cast("char", fan_index))
        return fan_control_lib.HealthyTable_FanRPM()

    def get_cpu_temperature(self):
        cpu_temp_milli = fan_control_lib.Thermal_Read_Cpu_Temperature()
        if cpu_temp_milli == 0:
            sensors = psutil.sensors_temperatures()
            if "coretemp" in sensors:
                return int(sensors["coretemp"][0].current)
            else:
                raise Exception("Could not fetch CPU temperature.")
        return cpu_temp_milli

    def get_gpu_temperature(self):
        gpus = GPUtil.getGPUs()
        if gpus:
            return gpus[0].temperature
        return None

stop_monitoring_event = threading.Event()
log_cpu_info = False  # Log option for CPU/GPU info
fan_speed_adjusted = False

def monitor_fans(asus_control, cpu_temp_text, gpu_temp_text, fan1_text, fan2_text):
    try:
        while not stop_monitoring_event.is_set():
            try:
                cpu_temp = asus_control.get_cpu_temperature()
                gpu_temp = asus_control.get_gpu_temperature()

                root.after(0, lambda: canvas.itemconfig(cpu_temp_text, text=f"{cpu_temp} °C"))
                root.after(0, lambda: canvas.itemconfig(gpu_temp_text, text=f"{gpu_temp} °C" if gpu_temp is not None else "Error"))

                fan1_speed = asus_control.get_fan_speed(0)
                fan2_speed = asus_control.get_fan_speed(1) if asus_control.get_fan_count() > 1 else 0

                root.after(0, lambda: canvas.itemconfig(fan1_text, text=f"{fan1_speed} RPM"))
                root.after(0, lambda: canvas.itemconfig(fan2_text, text=f"{fan2_speed} RPM"))

                if log_cpu_info:  # Log CPU/GPU data if the option is enabled
                    print(f"CPU Temp: {cpu_temp}°C | GPU Temp: {gpu_temp}°C | CPU RPM: {fan1_speed} RPM | GPU RPM: {fan2_speed} RPM")

                fan1_percentage = (fan1_speed / MAX_FAN_SPEED) * 100 if fan1_speed else 0
                fan2_percentage = (fan2_speed / MAX_FAN_SPEED) * 100 if fan2_speed else 0

                average_percentage = (fan1_percentage + fan2_percentage) / 2


                displayed_percentage = min(average_percentage, 100)

                root.after(0, lambda: canvas.itemconfig(slider_value_text, text=f"Fan Speed: {int(displayed_percentage)}%"))
                slider_x_pos = SLIDER_START_X + (displayed_percentage * (SLIDER_END_X - SLIDER_START_X) // 100)
                root.after(0, lambda: canvas.coords(slider_marker, slider_x_pos - SLIDER_MARKER_RADIUS, SLIDER_Y - SLIDER_MARKER_RADIUS, slider_x_pos + SLIDER_MARKER_RADIUS, SLIDER_Y + SLIDER_MARKER_RADIUS))


            except Exception as e:
                log_error(e)
                messagebox.showerror("Error", f"An error occurred: {e}")

            time.sleep(MONITORING_INTERVAL)
    except Exception as e:
        log_error(e)
        messagebox.showerror("Error", f"An error occurred in the monitoring thread: {e}")


def stop_monitoring():
    stop_monitoring_event.set()
    asus_control.reset_fans()
    root.quit()

last_cpu_temp = None  # Initialize last_cpu_temp before the function is called

def adjust_fan_speed_by_temp():
    global fan_speed_adjusted, last_cpu_temp
    cpu_temp = asus_control.get_cpu_temperature()
    gpu_temp = asus_control.get_gpu_temperature()

    temp_diff = max(cpu_temp - TARGET_TEMP, gpu_temp - TARGET_TEMP if gpu_temp else 0)

    if temp_diff > 0:
        gradual_factor = math.exp(-temp_diff / 10.0)  # Gradual decay factor
        target_speed = MIN_FAN_SPEED_PERCENTAGE + (MAX_FAN_SPEED_PERCENTAGE - MIN_FAN_SPEED_PERCENTAGE) * gradual_factor
        target_speed = max(MIN_FAN_SPEED_PERCENTAGE, min(target_speed, MAX_FAN_SPEED_PERCENTAGE))

        asus_control.set_all_fans_speed(int(target_speed))
    else:
        asus_control.set_all_fans_speed(MIN_FAN_SPEED_PERCENTAGE)

    if last_cpu_temp is not None:
        time_step = MONITORING_INTERVAL
        temp_rate_of_change = (cpu_temp - last_cpu_temp) / time_step
        if abs(temp_rate_of_change) > TEMP_CHANGE_THRESHOLD:
            time.sleep(1)  # Delay to smooth adjustments
    last_cpu_temp = cpu_temp  # Update last_cpu_temp with current cpu_temp

    fan_speed_adjusted = True
    messagebox.showinfo("Fan Speed Adjusted", "Fan speeds have been adjusted gradually based on temperature.")



def update_progress_bar(value, max_value, progress_bar, progress_label):
    """Update the progress bar and display percentage."""
    progress_bar["value"] = value
    progress_bar["maximum"] = max_value
    progress_bar.update()
    
    percentage = (value / max_value) * 100
    progress_label.config(text=f"{percentage:.0f}%")  # Update the label with percentage

def calculate_fan_health(speed, fan_name):
    """Evaluate the health of a fan based on speed."""
    if speed < POOR_FAN_RPM:
        return f"{fan_name}: Poor (RPM: {speed})"
    elif speed < GOOD_FAN_RPM:
        return f"{fan_name}: Good (RPM: {speed})"
    elif speed < EXCELLENT_FAN_RPM:
        return f"{fan_name}: Very Good (RPM: {speed})"
    else:
        return f"{fan_name}: Excellent (RPM: {speed})"

def run_test(progress_bar, progress_label):
    """Run the fan speed test in a separate thread."""
    total_fan1_speed = total_fan2_speed = 0
    max_fan1_speed = max_fan2_speed = 0
    count = 0


    asus_control.set_all_fans_speed(0)
    time.sleep(2)  # Wait for fans to spin down


    for i in range(1, 101, TEST_RAMP_UP_STEP):
        asus_control.set_all_fans_speed(i)
        time.sleep(TEST_RAMP_UP_DELAY)
        update_progress_bar(i, 100 + TEST_READING_COUNT, progress_bar, progress_label)


    for i in range(TEST_READING_COUNT):
        time.sleep(TEST_READING_DELAY)
        fan1_speed = asus_control.get_fan_speed(0)
        fan2_speed = asus_control.get_fan_speed(1) if asus_control.get_fan_count() > 1 else 0

        total_fan1_speed += fan1_speed
        total_fan2_speed += fan2_speed
        max_fan1_speed = max(max_fan1_speed, fan1_speed)
        max_fan2_speed = max(max_fan2_speed, fan2_speed)
        count += 1

        update_progress_bar(100 + i + 1, 100 + TEST_READING_COUNT, progress_bar, progress_label)


    avg_fan1_speed = total_fan1_speed / count
    avg_fan2_speed = total_fan2_speed / count


    fan1_health_status = calculate_fan_health(avg_fan1_speed, "FAN CPU")
    fan2_health_status = calculate_fan_health(avg_fan2_speed, "FAN GPU")


    sync_status = "Good Sync" if abs(avg_fan1_speed - avg_fan2_speed) < SYNC_RPM_THRESHOLD else "Bad Sync"

  
    if avg_fan1_speed > GOOD_FAN_RPM and avg_fan2_speed > GOOD_FAN_RPM and sync_status == "Good Sync":
        verdict = "Fans are running optimally and synchronized. \nVerdict: Excellent."
    else:
        verdict = "Fans are not running optimally or are unsynchronized. \nVerdict: Needs attention."

    
    fan_health_message = (
        f"{fan1_health_status}\n"
        f"{fan2_health_status}\n"
        f"Sync Status: {sync_status}\n\n"
        f"{verdict}\n\n"
        f"Average FAN CPU Speed: {avg_fan1_speed} RPM\n"
        f"Average FAN GPU Speed: {avg_fan2_speed} RPM\n\n\n\n"
        f"Max FAN CPU Speed recorded: {max_fan1_speed} RPM\n"
        f"Max FAN GPU Speed recorded: {max_fan2_speed} RPM"
    )

   
    messagebox.showinfo("Fan Test Completed", fan_health_message)

   
    asus_control.reset_fans()

    
    progress_bar["text"] = "Test Completed"
    progress_bar["value"] = progress_bar["maximum"]
    progress_bar.update()

def test_fan():
    """Initialize the GUI and start the fan test in a separate thread."""
   
    root = tk.Tk()
    root.title("Testing Your Fans")

    
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
    progress_bar.pack(padx=10, pady=10)

   
    progress_label = tk.Label(root, text="0%")
    progress_label.pack(pady=5)

    
    test_thread = threading.Thread(target=run_test, args=(progress_bar, progress_label))
    test_thread.start()

   
    root.mainloop()





# working at that 

#def synchronize_fans():
#    try:
#        fan_count = asus_control.get_fan_count()
#
#        if fan_count < 1:
#            raise ValueError("No fans detected.")
#
#        fan1_speed = asus_control.get_fan_speed(0)
#        fan2_speed = asus_control.get_fan_speed(1) if fan_count > 1 else fan1_speed
#
#        min_safe_speed = 1500
#
#        # Set minimum safe speed for both fans if below the threshold
#        if fan1_speed < min_safe_speed:
#            fan1_speed = min_safe_speed
#        if fan2_speed < min_safe_speed:
#            fan2_speed = min_safe_speed
#
#        # Synchronize slower fan to match the faster fan
#        if fan1_speed < fan2_speed:
#            asus_control.set_fan_speed(fan2_speed, 0)  # Increase CPU fan speed to match GPU fan
#        elif fan2_speed < fan1_speed:
#            asus_control.set_fan_speed(fan1_speed, 1)  # Increase GPU fan speed to match CPU fan
#
#        # Retrieve new fan speeds after synchronization
#        fan1_speed_after = asus_control.get_fan_speed(0)
#        fan2_speed_after = asus_control.get_fan_speed(1)
#
#        # Confirm synchronization
#        if fan1_speed_after == fan2_speed_after:
#            messagebox.showinfo("Fan Synchronization", f"Fans synchronized at {fan1_speed_after} RPM.")
#        else:
#            messagebox.showwarning("Fan Synchronization", "Fan synchronization failed or fans are still at different speeds.")
#
#    except ValueError as e:
#        messagebox.showerror("Error", f"Error: {e}")
#        log_error(e)
#    except Exception as e:
#        messagebox.showerror("Error", f"An error occurred during fan synchronization: {e}")
#        log_error(e)



root = tk.Tk()
root.title("Fan Control and Monitoring")
root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
root.attributes('-alpha', 0.97)
root.configure(bg=BG_COLOR)
root.iconbitmap("icon.ico")
root.resizable(False, False)
menu_bar = tk.Menu(root)

# Options menu
options_menu = tk.Menu(menu_bar, tearoff=0)
options_menu.add_checkbutton(label="Log CPU/RPM & Frequencies", variable=tk.IntVar(value=log_cpu_info), command=lambda: toggle_log())
options_menu.add_command(label="Adjust Fan Speed", command=adjust_fan_speed_by_temp)
options_menu.add_command(label="Test Fan", command=test_fan)
menu_bar.add_cascade(label="Options", menu=options_menu)
# options_menu.add_command(label="Synchronize Fans", command=synchronize_fans) -- not working correctly
root.config(menu=menu_bar)

canvas = tk.Canvas(root, bg=BG_COLOR, highlightthickness=0, bd=0)
canvas.pack(fill=tk.BOTH, expand=True)

# Create CPU, GPU, Fan speed labels
cpu_frame = canvas.create_rectangle(50, 50, 550, 100, fill=FRAME_COLOR, outline=OUTLINE_COLOR, width=2)
cpu_text = canvas.create_text(75, 75, text="CPU Temperature:", anchor="w", font=("Segoe UI", 14), fill=TEXT_COLOR)
cpu_temp_text = canvas.create_text(525, 75, text="0 °C", anchor="e", font=("Segoe UI", 14), fill=ACCENT_COLOR)

gpu_frame = canvas.create_rectangle(50, 110, 550, 160, fill=FRAME_COLOR, outline=OUTLINE_COLOR, width=2)
gpu_text = canvas.create_text(75, 135, text="GPU Temperature:", anchor="w", font=("Segoe UI", 14), fill=TEXT_COLOR)
gpu_temp_text = canvas.create_text(525, 135, text="0 °C", anchor="e", font=("Segoe UI", 14), fill=ACCENT_COLOR)

fan1_frame = canvas.create_rectangle(50, 170, 550, 220, fill=FRAME_COLOR, outline=OUTLINE_COLOR, width=2)
fan1_text_label = canvas.create_text(75, 195, text="FAN CPU Speed:", anchor="w", font=("Segoe UI", 14), fill=TEXT_COLOR)
fan1_text = canvas.create_text(525, 195, text="0 RPM", anchor="e", font=("Segoe UI", 14), fill=ACCENT_COLOR)

fan2_frame = canvas.create_rectangle(50, 230, 550, 280, fill=FRAME_COLOR, outline=OUTLINE_COLOR, width=2)
fan2_text_label = canvas.create_text(75, 255, text="FAN GPU Speed:", anchor="w", font=("Segoe UI", 14), fill=TEXT_COLOR)
fan2_text = canvas.create_text(525, 255, text="0 RPM", anchor="e", font=("Segoe UI", 14), fill=ACCENT_COLOR)

slider_position = 100
slider_line = canvas.create_line(SLIDER_START_X, SLIDER_Y, SLIDER_END_X, SLIDER_Y, width=5, fill=SLIDER_COLOR)
slider_marker = canvas.create_oval(SLIDER_START_X - SLIDER_MARKER_RADIUS, SLIDER_Y - SLIDER_MARKER_RADIUS, SLIDER_START_X + SLIDER_MARKER_RADIUS, SLIDER_Y + SLIDER_MARKER_RADIUS, fill=SLIDER_COLOR, outline=ACCENT_COLOR)
slider_value_text = canvas.create_text(300, 340, text=f"Fan Speed: 0%", font=("Segoe UI", 14), fill=TEXT_COLOR)

canvas.itemconfig(slider_marker, state="hidden")
canvas.itemconfig(slider_value_text, state="hidden")
canvas.itemconfig(slider_line, state="hidden")

slider_moved = False

def move_slider(event):
    global slider_position, slider_moved
    if SLIDER_START_X <= event.x <= SLIDER_END_X:
        slider_position = min(100, (event.x - SLIDER_START_X) * 100 // (SLIDER_END_X - SLIDER_START_X))
        
        canvas.coords(slider_marker, event.x - SLIDER_MARKER_RADIUS, SLIDER_Y - SLIDER_MARKER_RADIUS, event.x + SLIDER_MARKER_RADIUS, SLIDER_Y + SLIDER_MARKER_RADIUS)
        canvas.itemconfig(slider_value_text, text=f"Fan Speed: {slider_position}%")
        if not slider_moved:
            slider_moved = True


def release_slider(event):
    global slider_position, slider_moved
    if slider_moved:
        asus_control.set_all_fans_speed(slider_position)
    slider_moved = False

canvas.bind("<B1-Motion>", move_slider)
canvas.bind("<ButtonRelease-1>", release_slider)

def on_enter(event):
    stop_button.config(bg=BUTTON_ACTIVE_COLOR)

def on_leave(event):
    stop_button.config(bg=BUTTON_COLOR)

def start_fan_control():
    start_button.pack_forget()  
    canvas.itemconfig(slider_marker, state="normal")  
    canvas.itemconfig(slider_value_text, state="normal")  
    canvas.itemconfig(slider_line, state="normal") 
    stop_button.pack()  
    canvas.itemconfig(start_button_window, state="hidden") 

def stop_fan_control():
    asus_control.reset_fans()
    canvas.itemconfig(slider_marker, state="hidden")
    canvas.itemconfig(slider_value_text, state="hidden")
    canvas.itemconfig(slider_line, state="hidden")
    canvas.itemconfig(start_button_window, state="normal")
    stop_button.pack_forget()

start_button = tk.Button(
    root,
    text="Start Fan",
    command=start_fan_control,
    font=("Segoe UI", 12, "bold"),
    fg=TEXT_COLOR,
    bg=BUTTON_COLOR,
    activebackground=BUTTON_ACTIVE_COLOR,
    relief="flat",
    padx=20,
    pady=10,
)

start_button_window = canvas.create_window(300, 400, anchor="center", window=start_button)

stop_button = tk.Button(
    root,
    text="Close Fan",
    command=stop_fan_control,
    font=("Segoe UI", 12, "bold"),
    fg=TEXT_COLOR,
    bg=BUTTON_COLOR,
    activebackground=BUTTON_ACTIVE_COLOR,
    relief="flat",
    padx=20,
    pady=10,
)

def toggle_log():
    global log_cpu_info
    log_cpu_info = not log_cpu_info

def on_closing():
    if messagebox.askokcancel("Exit", "Do you want to exit the application?"):
        stop_monitoring()
def log_error(e):
    with open("error_log.txt", "a") as f:
        f.write("Error occurred:\n")
        f.write(str(e) + "\n")
        f.write(traceback.format_exc())
        f.write("-" * 50 + "\n")

root.protocol("WM_DELETE_WINDOW", on_closing)

try:
    asus_control = AsusControl()

    monitor_thread = threading.Thread(target=monitor_fans, args=(asus_control, cpu_temp_text, gpu_temp_text, fan1_text, fan2_text), daemon=True)
    monitor_thread.start()

    root.mainloop()

except Exception as e:
    log_error(e)
    messagebox.showerror("Error", f"An error occurred: {e}")
