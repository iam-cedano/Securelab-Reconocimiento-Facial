"""Run one firmware polling cycle with a file-backed camera in CPython."""

import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from firmware.capture_client import CaptureClient, run_capture_cycle


class Response:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.text = body.decode("utf-8")

    def close(self):
        pass


class StdlibTransport:
    @staticmethod
    def _request(method, url, headers, data=None):
        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return Response(response.status, response.read())
        except urllib.error.HTTPError as error:
            return Response(error.code, error.read())

    def get(self, url, headers):
        return self._request("GET", url, headers)

    def post(self, url, headers, data):
        return self._request("POST", url, headers, data)


class FileCamera:
    # Valid enough for upload testing; use PHOTO_FILE for an actual photograph.
    FALLBACK_JPEG = b"\xff\xd8\xff\xe0" + b"ESP32-CAM-SIMULATION" + b"\xff\xd9"

    def __init__(self, path):
        self.path = path

    def capture(self):
        if not self.path:
            return self.FALLBACK_JPEG
        with open(self.path, "rb") as image:
            return image.read()


def required_environment(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit("%s must be set" % name)
    return value


def main():
    client = CaptureClient(
        required_environment("SUPABASE_FUNCTION_URL"),
        required_environment("DEVICE_API_TOKEN"),
        os.environ.get("DEVICE_ID", "docker-camera"),
        StdlibTransport(),
    )
    completed = run_capture_cycle(
        client,
        FileCamera(os.environ.get("PHOTO_FILE")),
    )
    if completed:
        print("Uploaded %s to %s" % (
            completed["capture_id"],
            completed["object_path"],
        ))
    else:
        print("No pending facial capture")


if __name__ == "__main__":
    main()
