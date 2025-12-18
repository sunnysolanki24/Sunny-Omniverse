import json
import threading
import asyncio

import omni.ui as ui
import omni.ui.scene as sc
from omni.ui import color as cl
from omni.kit.viewport.utility import get_active_viewport_window

import paho.mqtt.client as mqtt

# ============================================================
# MQTT CONFIG
# ============================================================

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "ro/plant/telemetry"

# ============================================================
# LABEL POSITIONS (WORLD SPACE)
# ============================================================

WATER_LEVEL_POS = (0.0, 600.0, 650.0)   # On tank
FLOW_RATE_POS   = (0.0, 200.0, 120.0) # Offset location (adjust freely)

# ============================================================
# GLOBAL STATE
# ============================================================

scene_view = None
water_label = None
flow_label = None

latest_water = "--"
latest_flow = "--"

MAIN_LOOP = asyncio.get_running_loop()

# ============================================================
# SCENE SETUP (DOCUMENTED API ONLY)
# ============================================================

def setup_scene_text():
    global scene_view, water_label, flow_label

    viewport = get_active_viewport_window()
    if not viewport:
        print("❌ No active viewport")
        return

    with viewport.get_frame("tank_telemetry_labels"):
        scene_view = sc.SceneView()

        with scene_view.scene:

            # -------------------------------
            # WATER LEVEL LABEL
            # -------------------------------
            with sc.Transform(
                transform=sc.Matrix44.get_translation_matrix(*WATER_LEVEL_POS),
                look_at=sc.Transform.LookAt.CAMERA,
            ):
                water_label = sc.Label(
                    "Water Level: -- m",
                    alignment=ui.Alignment.CENTER,
                    color=cl("#00FFFF"),
                    size=32,
                )

            # -------------------------------
            # FLOW RATE LABEL
            # -------------------------------
            with sc.Transform(
                transform=sc.Matrix44.get_translation_matrix(*FLOW_RATE_POS),
                look_at=sc.Transform.LookAt.CAMERA,
            ):
                flow_label = sc.Label(
                    "Flow Rate: -- L/s",
                    alignment=ui.Alignment.CENTER,
                    color=cl("#FFD700"),
                    size=28,
                )

        viewport.viewport_api.add_scene_view(scene_view)

    print("✅ Water + Flow labels created")

# ============================================================
# SAFE UI UPDATE
# ============================================================

def update_labels():
    if water_label:
        water_label.text = f"Water Level: {latest_water} m"
    if flow_label:
        flow_label.text = f"Flow Rate: {latest_flow} L/s"

# ============================================================
# MQTT CALLBACKS
# ============================================================

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("✅ MQTT connected")
        client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global latest_water, latest_flow

    try:
        payload = json.loads(msg.payload.decode())

        wl = payload.get("water_level_m", "--")
        fr = payload.get("flow_rate_lps", "--")

        latest_water = f"{wl:.2f}" if isinstance(wl, (int, float)) else "--"
        latest_flow  = f"{fr:.2f}" if isinstance(fr, (int, float)) else "--"

        MAIN_LOOP.call_soon_threadsafe(update_labels)

    except Exception as e:
        print("❌ MQTT parse error:", e)

# ============================================================
# MQTT THREAD
# ============================================================

def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# ============================================================
# START
# ============================================================

setup_scene_text()

threading.Thread(
    target=start_mqtt,
    daemon=True
).start()

print("🚀 Water level + Flow rate display running")

