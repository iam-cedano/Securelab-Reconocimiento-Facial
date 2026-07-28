import json
import unittest

from firmware.capture_client import (
    CaptureApiError,
    CaptureClient,
    run_capture_cycle,
)


class FakeResponse:
    def __init__(self, status_code, payload=""):
        self.status_code = status_code
        self.text = payload
        self.closed = False

    def close(self):
        self.closed = True


class FakeTransport:
    def __init__(self, get_response=None, post_response=None):
        self.get_response = get_response
        self.post_response = post_response
        self.post_call = None

    def get(self, url, headers):
        return self.get_response

    def post(self, url, headers, data):
        self.post_call = (url, headers, data)
        return self.post_response


class FakeCamera:
    def __init__(self, jpeg=b"\xff\xd8photo\xff\xd9"):
        self.jpeg = jpeg
        self.calls = 0

    def capture(self):
        self.calls += 1
        return self.jpeg


class CaptureClientTests(unittest.TestCase):
    def client(self, transport):
        return CaptureClient(
            "https://example.supabase.co/functions/v1/camera-capture/",
            "token",
            "camera-1",
            transport,
        )

    def test_no_pending_capture_does_not_use_camera(self):
        response = FakeResponse(204)
        transport = FakeTransport(get_response=response)
        camera = FakeCamera()

        result = run_capture_cycle(self.client(transport), camera)

        self.assertIsNone(result)
        self.assertEqual(camera.calls, 0)
        self.assertTrue(response.closed)

    def test_claims_takes_and_uploads_photo(self):
        claim = FakeResponse(200, json.dumps({"id": "capture-id"}))
        uploaded = FakeResponse(
            200,
            json.dumps({"object_path": "capturas-faciales/capture-id/photo.jpg"}),
        )
        transport = FakeTransport(claim, uploaded)
        camera = FakeCamera()

        result = run_capture_cycle(self.client(transport), camera)

        self.assertEqual(result["capture_id"], "capture-id")
        self.assertEqual(camera.calls, 1)
        self.assertEqual(transport.post_call[2], camera.jpeg)
        self.assertEqual(transport.post_call[1]["x-capture-id"], "capture-id")
        self.assertEqual(
            transport.post_call[1]["Content-Length"],
            str(len(camera.jpeg)),
        )
        self.assertTrue(claim.closed)
        self.assertTrue(uploaded.closed)

    def test_api_error_includes_response_and_closes_it(self):
        response = FakeResponse(401, '{"error":"unauthorized device"}')
        transport = FakeTransport(get_response=response)

        with self.assertRaisesRegex(CaptureApiError, "401"):
            self.client(transport).claim_pending()

        self.assertTrue(response.closed)

    def test_empty_camera_frame_is_rejected_before_http_request(self):
        transport = FakeTransport(
            FakeResponse(200, json.dumps({"id": "capture-id"})),
        )

        with self.assertRaisesRegex(CaptureApiError, "empty image"):
            run_capture_cycle(self.client(transport), FakeCamera(b""))

        self.assertIsNone(transport.post_call)


if __name__ == "__main__":
    unittest.main()
