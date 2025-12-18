import omni.ui as ui
import omni.ui.scene as sc
from omni.ui import color as cl
from omni.kit.viewport.utility import get_active_viewport_window

# ============================================================
# TANK WORLD DATA (replace with your computed values)
# ============================================================

TANK_MIN_Y = 120.0
TANK_MAX_Y = 620.0
TANK_X = 0.0
TANK_Z = 650.0

# ============================================================
# GLOBAL STATE
# ============================================================

scene_view = None
level_transform = None
current_level_pct = 50.0

# ============================================================
# LEVEL → WORLD Y
# ============================================================

def level_pct_to_y(level_pct: float) -> float:
    return TANK_MIN_Y + (TANK_MAX_Y - TANK_MIN_Y) * (level_pct / 100.0)

# ============================================================
# SCENE SETUP
# ============================================================

def setup_level_indicator():
    global scene_view, level_transform

    viewport_window = get_active_viewport_window()
    if viewport_window is None:
        print("❌ No active viewport found")
        return

    with viewport_window.get_frame("water_level_indicator"):
        scene_view = sc.SceneView()

        with scene_view.scene:
            level_transform = sc.Transform(
                transform=sc.Matrix44.get_translation_matrix(
                    TANK_X,
                    level_pct_to_y(current_level_pct),
                    TANK_Z
                ),
                look_at=sc.Transform.LookAt.CAMERA
            )

            with level_transform:
                # --------------------------------------------------
                # Vertical yellow level line
                # --------------------------------------------------
                sc.Line(
                    start=(0, -60, 0),
                    end=(0, 40, 0),
                    color=cl("#FFD700"),
                    thickness=4,
                )

                # --------------------------------------------------
                # Arrow head (two lines)
                # --------------------------------------------------
                sc.Line(
                    start=(0, 40, 0),
                    end=(-15, 20, 0),
                    color=cl("#FFD700"),
                    thickness=4,
                )

                sc.Line(
                    start=(0, 40, 0),
                    end=(15, 20, 0),
                    color=cl("#FFD700"),
                    thickness=4,
                )

        viewport_window.viewport_api.add_scene_view(scene_view)

    print("✅ Water level arrow indicator created")

# ============================================================
# UPDATE WATER LEVEL (Y-ONLY MOVE)
# ============================================================

def set_water_level(level_pct: float):
    global current_level_pct

    current_level_pct = max(0.0, min(100.0, level_pct))
    new_y = level_pct_to_y(current_level_pct)

    if level_transform:
        level_transform.transform = sc.Matrix44.get_translation_matrix(
            TANK_X,
            new_y,
            TANK_Z
        )

# ============================================================
# START
# ============================================================

setup_level_indicator()

# Test motion
# set_water_level(10)
# set_water_level(50)
# set_water_level(90)

