"""HTTP adapter for MicroPython's urequests module."""

import gc

import urequests


class MicroPythonTransport:
    def get(self, url, headers):
        gc.collect()
        return urequests.get(url, headers=headers)

    def post(self, url, headers, data):
        gc.collect()
        return urequests.post(url, headers=headers, data=data)
