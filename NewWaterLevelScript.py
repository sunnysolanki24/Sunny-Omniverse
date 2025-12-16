# ============================================================
# MQTT → WATER LEVEL VISUALIZATION
# FINAL FIX (ASYNCIO LOOP CAPTURED CORRECTLY)
# ============================================================

import json
import threading
import asyncio

import omni.usd
import omni.ui as ui

from pxr import UsdGeom, Gf
import paho.mqtt.client as mqtt

# ============================================================
# CONFIG
# ============================================================

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "ro/plant/telemetry"

WATER_PRIM_PATH = "/World/Factory_Lite/ro_usd/PRODUCT_TANK/tank_2/water_volume"
MAX_WATER_HEIGHT_M = 5.0

# ============================================================
# USD SETUP (MAIN THREAD)
# ============================================================

stage = omni.usd.get_context().get_stage()
if not stage:
    raise RuntimeError("USD Stage not loaded")

water_prim = stage.GetPrimAtPath(WATER_PRIM_PATH)
if not water_prim.IsValid():
    raise RuntimeError(f"Water volume not found at {WATER_PRIM_PATH}")

xform = UsdGeom.Xform(water_prim)

scale_op = None
translate_op = None

for op in xform.GetOrderedXformOps():
    if op.GetOpType() == UsdGeom.XformOp.TypeScale:
        scale_op = op
    elif op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
        translate_op = op

if not scale_op:
    scale_op = xform.AddScaleOp()
if not translate_op:
    translate_op = xform.AddTranslateOp()

print("Water volume ready")

# ============================================================
# HUD UI (STABLE)
# ============================================================

window = ui.Window(
    "Tank Telemetry",
    width=300,
    height=80
)

with window.frame:
    tank_label = ui.Label(
        "Water Level: -- m",
        font_size=18
    )

print("HUD text initialized")

# ============================================================
# CAPTURE KIT ASYNCIO LOOP (CRITICAL STEP)
# ============================================================

MAIN_LOOP = asyncio.get_running_loop()
print("Main asyncio loop captured")

# ============================================================
# THREAD-SAFE UPDATE (RUNS ON KIT LOOP)
# ============================================================

latest_water_level = None

def update_scene():
    if latest_water_level is None:
        return

    level = max(0.0, min(latest_water_level, MAX_WATER_HEIGHT_M))

    scale_z = max(level / MAX_WATER_HEIGHT_M, 0.01)

    # Scale water UP in Z
    scale_op.Set(Gf.Vec3d(1.0, 1.0, scale_z))

    # Move base so it fills from bottom
    translate_op.Set(Gf.Vec3d(0.0, 0.0, level / 2.0))

    tank_label.text = f"Water Level: {level:.2f} m"


# ============================================================
# MQTT CALLBACKS (BACKGROUND THREAD)
# ============================================================

def on_connect(client, userdata, flags, rc, properties):
    if rc == 0:
        print("MQTT connected")
        client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global latest_water_level
    try:
        payload = json.loads(msg.payload.decode())
        latest_water_level = float(payload.get("water_level_m", 0.0))

        # ✅ Correct cross-thread scheduling
        MAIN_LOOP.call_soon_threadsafe(update_scene)

    except Exception as e:
        print("MQTT error:", e)

# ============================================================
# MQTT THREAD
# ============================================================

def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

threading.Thread(target=start_mqtt, daemon=True).start()

print("MQTT listener started")

