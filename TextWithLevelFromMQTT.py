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
# GLOBAL STATE
# ============================================================

scene_view = None
label = None
latest_value = "--"

MAIN_LOOP = asyncio.get_running_loop()

# ============================================================
# SCENE SETUP (DOCUMENTED API ONLY)
# ============================================================

def setup_scene_text():
    global scene_view, label

    viewport_window = get_active_viewport_window()
    if viewport_window is None:
        print("No active viewport found.")
        return

    with viewport_window.get_frame("mqtt_scene_text"):
        scene_view = sc.SceneView()

        with scene_view.scene:
            with sc.Transform(
                transform=sc.Matrix44.get_translation_matrix(0, 150, 0),
                look_at=sc.Transform.LookAt.CAMERA,
            ):
                label = sc.Label(
                    "Level: -- m",
                    alignment=ui.Alignment.CENTER,
                    color=cl("#00ffff"),
                    size=32,
                )

        viewport_window.viewport_api.add_scene_view(scene_view)

    print("SceneView attached and label created")

# ============================================================
# SAFE UI UPDATE (NO ui.execute)
# ============================================================

def update_label_text():
    if label:
        label.text = f"Water Level: {latest_value} m"

# ============================================================
# MQTT CALLBACKS
# ============================================================

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("MQTT connected")
        client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global latest_value

    try:
        payload = json.loads(msg.payload.decode())
        latest_value = payload.get("water_level_m", "--")

        # Schedule update on Kit main loop
        MAIN_LOOP.call_soon_threadsafe(update_label_text)

    except Exception as e:
        print("MQTT parse error:", e)

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

print("MQTT listener started")

