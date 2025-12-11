import omni.kit.app
import threading
import json
import paho.mqtt.client as mqtt
import omni.graph.core as og # Keep og import for variable access
from pxr import Usd, UsdGeom, Sdf, Gf, UsdShade, Tf
import omni.usd

# --- CONFIGURATION ---
GRAPH_PATH = "/World/ROPlantDataGraph" 
TANK_LEVEL_VAR_PATH = "/World/ROPlantDataGraph.graph:variable:Tank_Level"
WATER_PRIM_PATH = Sdf.Path("/World/Factory_Lite/ro_usd/PRODUCT_TANK/tank_2/oil_tank/Water_Volume_Prim") 

## 1. MQTT CONNECTOR SETUP
class MqttConnector:
    """Handles MQTT subscription and writes data to OmniGraph."""
    def __init__(self, broker="localhost", port=1883, topic="ro/plant/telemetry", og_variable_path=TANK_LEVEL_VAR_PATH):
        # Using VERSION2 (requires updated callback signatures)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2) 
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.topic = topic
        self.broker = broker
        self.port = port
        self.thread = None
        self.og_variable_path = og_variable_path

    def on_connect(self, client, userdata, flags, rc, properties): 
        if rc == 0:
            print(f"MQTT: Connected successfully. Subscribing to topic: {self.topic}")
            client.subscribe(self.topic)
        else:
            print(f"MQTT: Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        """Processes payload and writes tank_level to OmniGraph."""
        payload = msg.payload.decode()
        
        try:
            data = json.loads(payload)
            tank_level = data.get("water_level_m")
            
            # --- CORE ACTION: Write to OmniGraph Variable ---
            if tank_level is not None:
                # This line requires the variable input to exist in the graph!
                og.get_node_attribute(self.og_variable_path).set(float(tank_level))

        except json.JSONDecodeError:
            print(f"MQTT: Failed to decode JSON payload: {payload}")
        except Exception as e:
            # We skip the error here if the graph isn't fully set up yet
            pass 

    def start(self):
        """Start the MQTT client loop in a separate thread."""
        try:
            self.client.connect(self.broker, self.port, 60)
            self.thread = threading.Thread(target=self.client.loop_forever)
            self.thread.daemon = True 
            self.thread.start()
            print(f"MQTT: Connector thread started, connecting to {self.broker}...")
        except Exception as e:
            print(f"MQTT: Failed to start: {e}")

    def stop(self):
        """Cleanly stop the client."""
        self.client.loop_stop()
        self.client.disconnect()
        if self.thread:
            self.thread.join(timeout=1) 
        print("MQTT: Connector stopped.")

# --- MQTT Execution ---
if 'connector_instance' in globals():
    connector_instance.stop() 

connector_instance = MqttConnector()
connector_instance.start()


## 2. V-1: VISUAL SETUP (Water Cube and Material)
try:
    context = omni.usd.get_context()
    stage = context.get_stage() 
    if not stage:
        raise RuntimeError("No USD stage is currently open or loaded.")
except Exception as e:
    raise RuntimeError(f"FATAL ERROR: Could not get USD Stage. {e}")

TANK_PRIM_PATH = Sdf.Path("/World/Factory_Lite/ro_usd/PRODUCT_TANK/tank_2/oil_tank")
if not stage.GetPrimAtPath(TANK_PRIM_PATH):
    raise RuntimeError(f"Error: Parent tank prim not found at {TANK_PRIM_PATH}. Aborting.")

# --- Delete existing prim for clean run ---
existing_water_prim = stage.GetPrimAtPath(WATER_PRIM_PATH)
if existing_water_prim.IsValid():
    stage.RemovePrim(WATER_PRIM_PATH)
    print(f"⚠️ Removed existing Water Prim at: {WATER_PRIM_PATH}")

# --- Create Water Cube and set max scale/initial position ---
water_xform = UsdGeom.Xform.Define(stage, WATER_PRIM_PATH)
water_geom = UsdGeom.Cube.Define(stage, WATER_PRIM_PATH)
water_geom.GetSizeAttr().Set(1.0) 

scale_op = water_xform.AddScaleOp()
translate_op = water_xform.AddTranslateOp()
scale_op.Set(Gf.Vec3d(2.0, 2.0, 3.0)) # Max scale (2x2x3)
translate_op.Set(Gf.Vec3d(0.0, 0.0, 1.5)) # Centered and sitting on Z=0
print("✅ V-1: Water Prim created with initial max scale.")

# --- Create and Bind Material ---
WATER_MAT_PATH = Sdf.Path("/World/Looks/WaterMaterial")
water_mat_prim = stage.GetPrimAtPath(WATER_MAT_PATH)
if not water_mat_prim:
    water_mat_prim = UsdShade.Material.Define(stage, WATER_MAT_PATH).GetPrim()
    shader_path = WATER_MAT_PATH.AppendChild("Shader")
    shader = UsdShade.Shader.Define(stage, shader_path)
    shader.CreateIdAttr().Set(Tf.Token("omniPBR.mdl")) 
    shader.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.1, 0.4, 0.8)) 
    shader.CreateInput("opacity_constant", Sdf.ValueTypeNames.Float).Set(0.7)
    shader.CreateInput("emissive_color_constant", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.01, 0.01, 0.01)) 
    water_mat_prim.CreateSurfaceOutput().ConnectToSource(shader.CreateOutput("surface", Sdf.ValueTypeNames.Token))

material_to_bind = UsdShade.Material(water_mat_prim) 
UsdShade.MaterialBindingAPI(water_geom.GetPrim()).Bind(material_to_bind)
print("✅ V-1: Material Bound. Visualization setup complete.")

# ----------------------------------------------------
# V-2 SECTION IS REMOVED. PROCEED TO MANUAL STEPS.
# ----------------------------------------------------
