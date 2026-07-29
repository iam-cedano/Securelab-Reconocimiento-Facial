WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"

SUPABASE_FUNCTION_URL = (
    "https://YOUR_PROJECT.supabase.co/functions/v1/camera-capture"
)
DEVICE_API_TOKEN = "same-long-random-secret-as-the-edge-function"
DEVICE_ID = "esp32-cam-01"
# Optional Supabase publishable/anon token if the deployed Edge Function still
# requires an Authorization header. Leave empty when verify_jwt = false works.
AUTHORIZATION_TOKEN = ""

POLL_INTERVAL_SECONDS = 5
WIFI_TIMEOUT_SECONDS = 20
