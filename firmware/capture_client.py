"""Small Supabase Edge Function client that also runs on MicroPython."""

try:
    import ujson as json
except ImportError:
    import json


class CaptureApiError(Exception):
    pass


class CaptureClient:
    def __init__(self, function_url, device_token, device_id, transport):
        self.function_url = function_url.rstrip("/")
        self.device_token = device_token
        self.device_id = device_id
        self.transport = transport

    def _headers(self):
        return {
            "x-device-token": self.device_token,
            "x-device-id": self.device_id,
        }

    @staticmethod
    def _error(response):
        try:
            detail = response.text
        except Exception:
            detail = "unknown response"
        return CaptureApiError("camera API returned %s: %s" % (response.status_code, detail))

    def claim_pending(self):
        response = None
        try:
            response = self.transport.get(
                self.function_url,
                headers=self._headers(),
            )
            if response.status_code == 204:
                return None
            if response.status_code != 200:
                raise self._error(response)
            payload = json.loads(response.text)
            capture_id = payload.get("id")
            if not capture_id:
                raise CaptureApiError("camera API response has no capture id")
            return payload
        finally:
            if response is not None:
                response.close()

    def upload(self, capture_id, jpeg):
        if not jpeg:
            raise CaptureApiError("camera returned an empty image")

        headers = self._headers()
        headers["x-capture-id"] = capture_id
        headers["Content-Type"] = "image/jpeg"
        headers["Content-Length"] = str(len(jpeg))

        response = None
        try:
            response = self.transport.post(
                self.function_url,
                headers=headers,
                data=jpeg,
            )
            if response.status_code != 200:
                raise self._error(response)
            return json.loads(response.text)
        finally:
            if response is not None:
                response.close()


def run_capture_cycle(client, camera):
    pending = client.claim_pending()
    if pending is None:
        return None

    jpeg = camera.capture()
    result = client.upload(pending["id"], jpeg)
    return {
        "capture_id": pending["id"],
        "object_path": result.get("object_path"),
    }
