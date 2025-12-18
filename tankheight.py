import omni.usd
from pxr import UsdGeom, Gf

PRIM_PATH = "/World/Factory_Lite/ro_usd/PRODUCT_TANK/tank_2/oil_tank"

def get_prim_height_world(prim_path: str):
    stage = omni.usd.get_context().get_stage()
    if not stage:
        raise RuntimeError("USD stage not loaded")

    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise RuntimeError(f"Prim not found: {prim_path}")

    # ✅ INCLUDE ALL PURPOSES (THIS IS THE KEY)
    bbox_cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [
            UsdGeom.Tokens.default_,
            UsdGeom.Tokens.render,
            UsdGeom.Tokens.proxy,
            UsdGeom.Tokens.guide,
        ],
        useExtentsHint=True
    )

    world_bound = bbox_cache.ComputeWorldBound(prim)
    bbox_range = world_bound.GetRange()

    if bbox_range.IsEmpty():
        raise RuntimeError(f"Bounding box empty for {prim_path}")

    min_pt = bbox_range.GetMin()
    max_pt = bbox_range.GetMax()

    height = max_pt[1] - min_pt[1]

    return height, min_pt, max_pt


# ---------------------------------------------------
# RUN
# ---------------------------------------------------
height, min_pt, max_pt = get_prim_height_world(PRIM_PATH)

print(f"✅ Oil tank height (meters): {height:.3f}")
print(f"🔹 Bottom Y: {min_pt[1]:.3f}")
print(f"🔹 Top Y:    {max_pt[1]:.3f}")

