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
# TANK WORLD COORDINATES (Z-UP)
# ============================================================

TANK_X = 0.0
TANK_Y = 600.0

TANK_BOTTOM_Z = 120.0
TANK_TOP_Z = 620.0
TANK_HEIGHT = TANK_TOP_Z - TANK_BOTTOM_Z  # = 500

# ============================================================
# WATER LEVEL RANGE (REAL DATA)
# ============================================================

WATER_LEVEL_MIN = 0.5
WATER_LEVEL_MAX = 5.0

# ============================================================
# GLOBAL STATE
# ============================================================

scene_view = None
arrow_transform = None
latest_level = WATER_LEVEL_MIN

MAIN_LOOP = asyncio.get_running_loop()

# ============================================================
# MAP WATER LEVEL → WORLD Z
# ============================================================

def level_to_world_z(level):
    # Clamp incoming data
    level = max(WATER_LEVEL_MIN, min(WATER_LEVEL_MAX, level))

    normalized = (
        (level - WATER_LEVEL_MIN)
        / (WATER_LEVEL_MAX - WATER_LEVEL_MIN)
    )

    return TANK_BOTTOM_Z + normalized * TANK_HEIGHT

# ============================================================
# SCENE SETUP
# ============================================================

def setup_level_indicator():
    global scene_view, arrow_transform

    viewport_window = get_active_viewport_window()
    if viewport_window is None:
        print("❌ No active viewport")
        return

    with viewport_window.get_frame("tank_level_indicator"):
        scene_view = sc.SceneView()

        with scene_view.scene:

            # ===================================================
            # STATIC BLUE VERTICAL LINE (WORLD-LOCKED)
            # ===================================================
            with sc.Transform(
                transform=(
                    sc.Matrix44.get_translation_matrix(
                        TANK_X, TANK_Y, TANK_BOTTOM_Z
                    )
                    * sc.Matrix44.get_scale_matrix(1.0, 1.0, TANK_HEIGHT)
                )
            ):
                sc.Line(
                    start=(0.0, 0.0, 0.0),
                    end=(0.0, 0.0, 1.0),  # unit Z line → scaled
                    color=cl("#1E90FF"),
                    thickness=4,
                )

            # ===================================================
            # YELLOW ARROW (MOVES ONLY IN Z)
            # ===================================================
            arrow_transform = sc.Transform(
                transform=sc.Matrix44.get_translation_matrix(
                    TANK_X,
                    TANK_Y,
                    level_to_world_z(latest_level),
                ),
                look_at=sc.Transform.LookAt.CAMERA,
            )

            with arrow_transform:
                # Shaft (starts at Z = 0 → FIXED)
                sc.Line(
                    start=(0.0, 0.0, 0.0),
                    end=(0.0, 0.0, 60.0),
                    color=cl("#FFD700"),
                    thickness=4,
                )

                # Arrow head
                sc.Line(
                    start=(0.0, 0.0, 60.0),
                    end=(-15.0, 0.0, 40.0),
                    color=cl("#FFD700"),
                    thickness=4,
                )

                sc.Line(
                    start=(0.0, 0.0, 60.0),
                    end=(15.0, 0.0, 40.0),
                    color=cl("#FFD700"),
                    thickness=4,
                )

        viewport_window.viewport_api.add_scene_view(scene_view)

    print("✅ Vertical tank indicator initialized")

# ============================================================
# UPDATE ARROW POSITION
# ============================================================

def update_indicator():
    if arrow_transform:
        arrow_transform.transform = sc.Matrix44.get_translation_matrix(
            TANK_X,
            TANK_Y,
            level_to_world_z(latest_level),
        )

# ============================================================
# MQTT CALLBACKS
# ============================================================

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("✅ MQTT connected")
        client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global latest_level

    try:
        payload = json.loads(msg.payload.decode())
        latest_level = float(payload.get("water_level_m", WATER_LEVEL_MIN))

        # Safe Kit main-thread update
        MAIN_LOOP.call_soon_threadsafe(update_indicator)

    except Exception as e:
        print("❌ MQTT error:", e)

# ============================================================
# MQTT THREAD
# ============================================================

def start_mqtt():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

# ============================================================
# START
# ============================================================

setup_level_indicator()

threading.Thread(
    target=start_mqtt,
    daemon=True
).start()

print("🚀 Tank level indicator running")

