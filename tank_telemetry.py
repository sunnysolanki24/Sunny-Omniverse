# tank_telemetry.py

water_level_m = 0.0

def set_water_level(value: float):
    global water_level_m
    water_level_m = value

def get_water_level():
    return water_level_m

