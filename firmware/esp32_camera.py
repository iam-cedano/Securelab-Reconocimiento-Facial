"""OV2640 adapter for ESP32 MicroPython builds that include `camera`."""

import camera


class Esp32Camera:
    def __init__(self):
        self.initialized = False

    def initialize(self):
        if self.initialized:
            return

        # AI-Thinker ESP32-CAM is camera id 0 in common camera-enabled builds.
        camera.init(0, format=camera.JPEG, fb_location=camera.PSRAM)
        camera.framesize(camera.FRAME_QVGA)
        camera.quality(12)
        self.initialized = True

    def capture(self):
        self.initialize()
        frame = camera.capture()
        if frame is None:
            raise RuntimeError("the OV2640 did not return a frame")
        return frame

    def close(self):
        if self.initialized:
            camera.deinit()
            self.initialized = False
