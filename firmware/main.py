"""Boot entry point for an ESP32-CAM running camera-enabled MicroPython."""

import gc
import time

import network

import config
from capture_client import CaptureClient, run_capture_cycle
from esp32_camera import Esp32Camera
from micropython_transport import MicroPythonTransport


def connect_wifi():
    station = network.WLAN(network.STA_IF)
    station.active(True)
    if station.isconnected():
        return station

    station.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    started = time.ticks_ms()
    timeout_ms = config.WIFI_TIMEOUT_SECONDS * 1000

    while not station.isconnected():
        if time.ticks_diff(time.ticks_ms(), started) >= timeout_ms:
            raise RuntimeError("Wi-Fi connection timed out")
        time.sleep_ms(250)

    print("Wi-Fi connected:", station.ifconfig()[0])
    return station


def main():
    camera = Esp32Camera()
    client = CaptureClient(
        config.SUPABASE_FUNCTION_URL,
        config.DEVICE_API_TOKEN,
        config.DEVICE_ID,
        MicroPythonTransport(),
    )

    while True:
        try:
            connect_wifi()
            completed = run_capture_cycle(client, camera)
            if completed:
                print("Uploaded:", completed["capture_id"], completed["object_path"])
        except Exception as error:
            print("Capture cycle failed:", error)
        finally:
            gc.collect()

        time.sleep(config.POLL_INTERVAL_SECONDS)


main()
