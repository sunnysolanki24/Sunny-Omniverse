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
# LABEL POSITION (ON PRODUCT TANK)
# ============================================================

# 🔧 Tuned to sit ON the product tank
# Adjust Y for height, Z for forward/back
TANK_LABEL_POSITION = (0.0, 600.0, 650.0)

# ============================================================
# GLOBAL STATE
# ============================================================

scene_view = None
label = None
latest_value = "--"

MAIN_LOOP = asyncio.get_running_loop()

# ============================================================
# SCENE SETUP (DOCUMENTED API ONLY)
# https://docs.omniverse.nvidia.com/kit/docs/omni.ui.scene/latest/omni.ui.scene
# ============================================================

def setup_scene_text():
    global scene_view, label

    viewport_window = get_active_viewport_window()
    if viewport_window is None:
        print("❌ No active viewport found.")
        return

    with viewport_window.get_frame("mqtt_scene_text"):
        scene_view = sc.SceneView()

        with scene_view.scene:
            with sc.Transform(
                transform=sc.Matrix44.get_translation_matrix(
                    TANK_LABEL_POSITION[0],
                    TANK_LABEL_POSITION[1],
                    TANK_LABEL_POSITION[2],
                ),
                look_at=sc.Transform.LookAt.CAMERA,  # ✅ rotate only
            ):
                label = sc.Label(
                    "Level: -- m",
                    alignment=ui.Alignment.CENTER,
                    color=cl("#00ffff"),
                    size=32,
                )

        viewport_window.viewport_api.add_scene_view(scene_view)

    print("✅ SceneView attached and label placed on product tank")

# ============================================================
# SAFE UI UPDATE (MAIN THREAD)
# ============================================================

def update_label_text():
    if label:
        label.text = f"Water Level: {latest_value} m"

# ============================================================
# MQTT CALLBACKS
# ============================================================

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("✅ MQTT connected")
        client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global latest_value

    try:
        payload = json.loads(msg.payload.decode())
        latest_value = payload.get("water_level_m", "--")

        # ✅ Correct Kit-safe UI update
        MAIN_LOOP.call_soon_threadsafe(update_label_text)

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

print("🚀 MQTT tank label running")

