import paho.mqtt.client as mqtt
import time
import json
import random

# --- CONFIGURATION ---
MQTT_BROKER = "localhost"  # Replace with your actual broker address (e.g., "test.mosquitto.org")
MQTT_PORT = 1883           # Standard MQTT port
TOPIC = "ro/plant/telemetry"
PUBLISH_INTERVAL_SEC = 1.0

# --- SIMULATION PARAMETERS ---
MAX_TANK_LEVEL = 5.0  # meters
MIN_TANK_LEVEL = 0.5  # meters
MAX_FLOW_RATE = 10.0  # liters per second
FLOW_RATE_BASE = 5.0
FLOW_RATE_NOISE = 0.5
LEVEL_CHANGE_RATE = 0.05 # Max level change per tick

# --- INITIAL STATE ---
current_tank_level = 2.5
is_filling = True # Simulate a pumping cycle

def on_connect(client, userdata, flags, rc):
    """Callback function executed when the client successfully connects."""
    if rc == 0:
        print(f"Successfully connected to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"Failed to connect, return code {rc}")

def simulate_data():
    """Generates dynamic, constrained water level and flow rate data."""
    global current_tank_level, is_filling

    # 1. Simulate Flow Rate (Dynamic input source)
    # Flow rate oscillates slightly around a base value, simulating pump noise or throttling
    flow_rate = FLOW_RATE_BASE + random.uniform(-FLOW_RATE_NOISE, FLOW_RATE_NOISE)
    flow_rate = round(max(0.0, flow_rate), 2) # Ensure flow rate is non-negative

    # 2. Simulate Tank Level (Simulate the effect of the flow rate)
    if is_filling:
        # Fill at a rate proportional to the flow rate (simplified model)
        current_tank_level += LEVEL_CHANGE_RATE * (flow_rate / MAX_FLOW_RATE)
        if current_tank_level >= MAX_TANK_LEVEL:
            current_tank_level = MAX_TANK_LEVEL
            is_filling = False # Stop filling, start emptying (or stabilizing)
    else:
        # Emptying/Stabilizing (simulating consumption or stabilization)
        current_tank_level -= LEVEL_CHANGE_RATE * 0.5
        if current_tank_level <= MIN_TANK_LEVEL:
            current_tank_level = MIN_TANK_LEVEL
            is_filling = True # Start filling again

    current_tank_level = round(current_tank_level, 3)

    # 3. Create JSON Payload
    payload = {
        "timestamp": time.time(),
        "asset_id": "TankA",
        "water_level_m": current_tank_level,
        "flow_rate_lps": flow_rate
    }
    return payload

def main():
    """Sets up the MQTT client and runs the simulation loop."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, "Omniverse_RO_PoC_Mock_Publisher")
    client.on_connect = on_connect

    try:
        # Attempt connection to the broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"Connection error: {e}. Ensure your MQTT broker is running at {MQTT_BROKER}:{MQTT_PORT}")
        return

    client.loop_start() # Start the non-blocking network loop

    print("\n--- RO SCADA Mock Data Stream Running ---")
    print(f"Publishing to topic: {TOPIC}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            data_payload = simulate_data()
            json_payload = json.dumps(data_payload)

            client.publish(TOPIC, json_payload)
            print(f" Published: {json_payload}")

            time.sleep(PUBLISH_INTERVAL_SEC)

    except KeyboardInterrupt:
        print("\nStopping mock publisher.")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()