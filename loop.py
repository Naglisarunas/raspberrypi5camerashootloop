import os
import time
from datetime import datetime

# libcamera is used to reference AwbModeEnum for manual white balance
import libcamera
from picamera2 import Picamera2

def create_output_directory(base_path: str) -> str:
    """
    Creates a timestamped output directory based on the current date and time.
    
    Example: If base_path = "/home/pi/Pictures", 
    this might create "/home/pi/Pictures/20250103_101500" (YYYYMMDD_HHMMSS).
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory = os.path.join(base_path, timestamp)
    os.makedirs(directory, exist_ok=True)
    return directory

# -----------------------------------------------------------------------------
#                           Configuration Section
# -----------------------------------------------------------------------------

# Path where images will be saved.
OUTPUT_BASE_PATH = "/media/nagli/aed29726-d3de-4f78-8450-0f34bb1faab11"

# Interval (in seconds) between each capture.
INTERVAL_SECONDS = 10

# Toggle between fully automatic (True) and manual (False) camera mode.
FULLY_AUTO_MODE = True  # Set to False to test manual exposure and gain control

# -----------------------------------------------------------------------------

#                             Auto Mode Settings
# -----------------------------------------------------------------------------
# In auto mode, you can still choose a resolution. The camera will handle
# exposure, white balance, etc. automatically.
AUTO_SETTINGS = {
    "resolution": (1920, 1080)
}

# -----------------------------------------------------------------------------
#                            Manual Mode Settings
# -----------------------------------------------------------------------------
# If FULLY_AUTO_MODE is False, these settings take effect.
# You have control over resolution, brightness, contrast, saturation, sharpness,
# exposure_time, and white_balance.
#
# - resolution: (width, height)
# - brightness: 0 to 100 (default: 50)
# - contrast:   -100 to 100 (default: 0)
# - saturation: -100 to 100 (default: 0)
# - sharpness:  -100 to 100 (default: 0)
# - exposure_time: microseconds. If None, uses auto exposure (AeEnable=True).
#   Example: 1000 => 1 ms; 5000 => 5 ms; 20000 => 20 ms, etc.
# - white_balance: one of ["auto", "incandescent", "fluorescent", "daylight", "cloudy"].
#   If "auto", AwbEnable = True; otherwise AwbEnable = False and set AwbMode.
#
# If you find your images are overexposed, lower 'exposure_time' or 
# lock the analog gain at 1.0 (see code below) to reduce brightness.
MANUAL_SETTINGS = {
    "resolution":   (640, 480),
    "brightness":   50,
    "contrast":     0,
    "saturation":   0,
    "sharpness":    0,
    "exposure_time": 1000,       # 1000 µs (1 ms). Lower if still too bright.
    "white_balance": "auto"      # "auto", "incandescent", "fluorescent", "daylight", "cloudy"
}

# Maps string-based white balance modes to libcamera enums
AWB_MODE_MAP = {
    "auto":         libcamera.controls.AwbModeEnum.Auto,
    "incandescent": libcamera.controls.AwbModeEnum.Incandescent,
    "fluorescent":  libcamera.controls.AwbModeEnum.Fluorescent,
    "daylight":     libcamera.controls.AwbModeEnum.Daylight,
    "cloudy":       libcamera.controls.AwbModeEnum.Cloudy
}

def main():
    """
    Main function: initializes the PiCamera2, configures it for either
    auto or manual mode, then captures images at fixed intervals.
    """
    picam = Picamera2()

    # -------------------------------------------------------------------------
    #               Configure Camera for Auto or Manual Mode
    # -------------------------------------------------------------------------
    if FULLY_AUTO_MODE:
        # AUTO mode: set only resolution, let camera handle everything else
        auto_config = picam.create_still_configuration(
            main={"size": AUTO_SETTINGS["resolution"]}
        )
        picam.configure(auto_config)
        print("[INFO] Camera configured for FULLY AUTO mode.")
        print("       - Resolution:", AUTO_SETTINGS["resolution"])
        print("       - Exposure, White Balance, etc. are automatic.")
    else:
        # MANUAL mode: specify resolution and custom controls
        manual_config = picam.create_still_configuration(
            main={"size": MANUAL_SETTINGS["resolution"]}
        )
        picam.configure(manual_config)

        # Build the controls dictionary
        controls = {
            "Brightness": MANUAL_SETTINGS["brightness"],
            "Contrast":   MANUAL_SETTINGS["contrast"],
            "Saturation": MANUAL_SETTINGS["saturation"],
            "Sharpness":  MANUAL_SETTINGS["sharpness"]
        }

        # -------------------------------
        # Handle Exposure
        # -------------------------------
        if MANUAL_SETTINGS["exposure_time"] is not None:
            # Manual exposure: disable auto exposure and set ExposureTime
            controls["AeEnable"] = False
            controls["ExposureTime"] = MANUAL_SETTINGS["exposure_time"]

            # Optionally lock analog gain at 1.0 to reduce overexposure further:
            # (only if your PiCamera2 + libcamera version supports it)
            controls["AnalogueGain"] = 1.0

            print(f"[INFO] Using manual exposure: {MANUAL_SETTINGS['exposure_time']} µs")
            print("[INFO] Locked AnalogueGain at 1.0 for minimal sensor amplification.")
        else:
            # Auto exposure
            controls["AeEnable"] = True
            print("[INFO] Auto exposure enabled.")

        # -------------------------------
        # Handle White Balance
        # -------------------------------
        wb_mode_str = MANUAL_SETTINGS["white_balance"].lower()
        if wb_mode_str in AWB_MODE_MAP:
            if wb_mode_str == "auto":
                # Auto white balance
                controls["AwbEnable"] = True
                print("[INFO] Auto white balance enabled.")
            else:
                # Manual white balance
                controls["AwbEnable"] = False
                controls["AwbMode"] = AWB_MODE_MAP[wb_mode_str]
                print(f"[INFO] White balance mode set to '{wb_mode_str}'.")
        else:
            # If invalid string, default to auto
            controls["AwbEnable"] = True
            print(f"[WARN] Unrecognized white_balance '{wb_mode_str}', defaulting to auto WB.")

        # Apply the manual controls
        picam.set_controls(controls)

        # Log settings
        print("[INFO] Camera configured for MANUAL mode with these settings:")
        print(f"       - Resolution:      {MANUAL_SETTINGS['resolution']}")
        print(f"       - Brightness:      {MANUAL_SETTINGS['brightness']}")
        print(f"       - Contrast:        {MANUAL_SETTINGS['contrast']}")
        print(f"       - Saturation:      {MANUAL_SETTINGS['saturation']}")
        print(f"       - Sharpness:       {MANUAL_SETTINGS['sharpness']}")
        print(f"       - ExposureTime:    {MANUAL_SETTINGS['exposure_time']}")
        print(f"       - White Balance:   {MANUAL_SETTINGS['white_balance']}")
        if MANUAL_SETTINGS['exposure_time'] is not None:
            print("       - AnalogueGain:    1.0 (locked)")

    # -------------------------------------------------------------------------
    #                    Start Camera and Create Output Folder
    # -------------------------------------------------------------------------
    picam.start()
    print("[INFO] Camera started.")

    output_directory = create_output_directory(OUTPUT_BASE_PATH)
    print(f"[INFO] Images will be saved in: {output_directory}")

    # -------------------------------------------------------------------------
    #            Image Capture Loop (Runs Until KeyboardInterrupt)
    # -------------------------------------------------------------------------
    try:
        print("[INFO] Starting image capture. Press Ctrl+C to stop.\n")
        while True:
            # Create a timestamped filename, e.g. "image_20250103_101500.jpg"
            timestamp_str = datetime.now().strftime("image_%Y%m%d_%H%M%S.jpg")
            file_path = os.path.join(output_directory, timestamp_str)

            # Capture the image
            print(f"[CAPTURE] Saving image: {file_path}")
            picam.capture_file(file_path)

            # Wait for the specified interval
            time.sleep(INTERVAL_SECONDS)

    except KeyboardInterrupt:
        # Gracefully handle Ctrl+C
        print("\n[INFO] Stopping image capture...")

    finally:
        # Stop the camera no matter how the loop ended
        picam.stop()
        print("[INFO] Camera stopped. Exiting.")

# -----------------------------------------------------------------------------
#                                  Run Script
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
