"""Parametric measuring scoop (laundry detergent, coffee, protein powder, ...).

The scoop is printed upright (opening facing up) with the handle lying flat on
the build plate, so the only overhangs are the outward flare of the cup wall
(`flare_angle` from vertical) and small 45° chamfers. No supports needed.

The cup is sized so that it holds exactly `volume` when filled to the brim
(inner floor fillet included).

This is a web-openscad-editor CadQuery model (build() is called with the
customizer values). It also runs locally:

    uv run python measuring-scoop.py 60 100
    uv run python measuring-scoop.py 75 --set cup.flare_angle=20 --step

On NixOS the OCP wheel needs libX11, libGL, libstdc++, expat and zlib on
LD_LIBRARY_PATH.
"""

import math

import cadquery as cq
from pydantic import BaseModel, Field


class Cup(BaseModel):
    aspect: float = Field(
        0.9, ge=0.4, le=2, multiple_of=0.05,
        description="Inner height divided by inner bottom diameter (shape of the cup)",
    )
    flare_angle: float = Field(
        15, ge=0, le=40, multiple_of=1,
        description="Outward lean of the cup wall in degrees from vertical. This is the steepest overhang",
    )
    wall: float = Field(2, ge=0.8, le=5, multiple_of=0.1, description="Wall thickness in mm")
    floor: float = Field(2, ge=0.8, le=5, multiple_of=0.1, description="Floor thickness in mm")
    inner_fillet: float = Field(
        6, ge=0, le=20, multiple_of=0.5,
        description="Fillet between inner floor and wall in mm. Makes scooping and rinsing easier",
    )
    bottom_chamfer: float = Field(
        0.6, ge=0, le=2, multiple_of=0.1, description="45° chamfer on the bottom edges in mm (against elephant foot)"
    )


class Handle(BaseModel):
    length: float = Field(75, ge=20, le=200, multiple_of=1, description="Handle length from the cup wall in mm")
    width_root: float = Field(14, ge=6, le=40, multiple_of=0.5, description="Handle width at the cup in mm")
    width_tip: float = Field(20, ge=6, le=40, multiple_of=0.5, description="Handle width at the tip in mm")
    thickness: float = Field(5, ge=2, le=15, multiple_of=0.5, description="Handle thickness in mm")
    rib_width: float = Field(
        5, ge=0, le=20, multiple_of=0.5, description="Width of the stiffening rib between handle and cup (0 to disable)"
    )
    rib_height: float = Field(
        0.6, ge=0, le=1, multiple_of=0.05, description="Rib height as a fraction of the cup height"
    )
    hang_hole: float = Field(
        7, ge=0, le=30, multiple_of=0.5, description="Diameter of the hanging hole in the tip (0 to disable)"
    )


class Label(BaseModel):
    show: bool = Field(True, description="Emboss a label on the handle")
    text: str = Field("", description='Label text. Empty: the volume, e.g. "60 ml"')
    size: float = Field(8, ge=3, le=20, multiple_of=0.5, description="Font size in mm")
    height: float = Field(0.6, ge=0.2, le=3, multiple_of=0.1, description="Emboss height in mm")


class Params(BaseModel):
    volume: float = Field(60, ge=5, le=1000, description="Capacity in ml, filled to the brim")
    cup: Cup = Field(Cup(), title="Cup")
    handle: Handle = Field(Handle(), title="Handle")
    label: Label = Field(Label(), title="Label")


def cavity_dims(c: Cup, rb: float) -> tuple[float, float]:
    """inner bottom radius -> (inner top radius, inner height)"""
    h = c.aspect * 2 * rb
    return rb + h * math.tan(math.radians(c.flare_angle)), h


def cavity(c: Cup, rb: float, extra: float = 0) -> cq.Workplane:
    """Inner cavity solid, floor at z=0, brim at z=h. `extra` extends it upwards
    (for a clean cut) while keeping the wall slope."""
    rt, h = cavity_dims(c, rb)
    tan = math.tan(math.radians(c.flare_angle))
    pts = [(0, 0), (rb, 0), (rt + extra * tan, h + extra), (0, h + extra)]
    solid = cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0))
    if c.inner_fillet > 0:
        solid = solid.faces("<Z").edges().fillet(c.inner_fillet)
    return solid


def solve_bottom_radius(c: Cup, volume_ml: float) -> float:
    """Inner bottom radius for which the cavity holds `volume_ml`.

    The volume of the plain frustum is K * rb³. The fillet removes a little; that
    loss changes slowly with rb, so iterate rb = cbrt((target + loss) / K)."""
    target = volume_ml * 1000
    tan = math.tan(math.radians(c.flare_angle))
    m = 1 + 2 * c.aspect * tan  # rt / rb
    k = math.pi * 2 * c.aspect / 3 * (1 + m + m * m)
    rb = (target / k) ** (1 / 3)
    for _ in range(20):
        if rb < c.inner_fillet * 1.5:
            raise ValueError(f"{volume_ml:g} ml is too small for an inner fillet of {c.inner_fillet:g} mm")
        try:
            actual = cavity(c, rb).val().Volume()
        except Exception as e:
            raise ValueError(f"cannot fillet the cup floor (bottom radius {rb:.1f} mm): {e}") from e
        if abs(actual - target) < target * 1e-5:
            return rb
        rb = ((target + k * rb**3 - actual) / k) ** (1 / 3)
    raise ValueError(f"could not size the cup for {volume_ml:g} ml")


def handle_outline(r1: float, r2: float, d: float) -> cq.Workplane:
    """2D hull of a circle r1 at the origin and a circle r2 at (d, 0)."""
    s = (r1 - r2) / d
    c = math.sqrt(1 - s * s)
    pts = [(r1 * s, r1 * c), (d + r2 * s, r2 * c), (d + r2 * s, -r2 * c), (r1 * s, -r1 * c)]
    return (
        cq.Workplane("XY")
        .moveTo(*pts[0])
        .lineTo(*pts[1])
        .threePointArc((d + r2, 0), pts[2])
        .lineTo(*pts[3])
        .threePointArc((-r1, 0), pts[0])
        .close()
    )


def build(p: Params) -> cq.Workplane:
    c, hd = p.cup, p.handle
    rb = solve_bottom_radius(c, p.volume)
    rt, h = cavity_dims(c, rb)
    theta = math.radians(c.flare_angle)
    tan = math.tan(theta)
    # horizontal wall thickness so that the perpendicular thickness is c.wall
    wall_h = c.wall / math.cos(theta)
    total_h = c.floor + h

    # outer body: frustum from the bed to the brim, wall parallel to the cavity
    rob = rb + wall_h - c.floor * tan  # outer radius at z=0
    rot = rt + wall_h
    ch = c.bottom_chamfer
    if ch > 0:
        outer_pts = [(0, 0), (rob - ch, 0), (rob + ch * tan, ch), (rot, total_h), (0, total_h)]
    else:
        outer_pts = [(0, 0), (rob, 0), (rot, total_h), (0, total_h)]
    body = cq.Workplane("XZ").polyline(outer_pts).close().revolve(360, (0, 0, 0), (0, 1, 0))

    if hd.hang_hole > 0 and hd.hang_hole > hd.width_tip - 6:
        raise ValueError(f"the hang hole can be at most handle tip width - 6 mm ({hd.width_tip - 6:g} mm)")

    # handle, flat on the bed
    tip_x = rob + hd.length - hd.width_tip / 2
    handle = handle_outline(hd.width_root / 2, hd.width_tip / 2, tip_x).extrude(hd.thickness)
    handle = handle.faces(">Z").edges().fillet(min(1.5, hd.thickness / 3))
    if ch > 0:
        handle = handle.faces("<Z").edges().chamfer(min(ch, hd.thickness / 4))
    body = body.union(handle)

    # rib: a triangle standing on the handle, leaning against the cup wall, 45° slope.
    # It stays one wall thickness below the rim so it doesn't touch the rim fillet.
    rib_end = rob  # where the rib's footprint on the handle ends
    if hd.rib_width > 0 and hd.rib_height > 0 and total_h - c.wall > hd.thickness:
        rib_top = hd.thickness + (total_h - c.wall - hd.thickness) * hd.rib_height
        x_wall_top = rob + rib_top * tan - 0.5  # slightly inside the wall for a clean union
        rise = rib_top - hd.thickness
        rib_end = x_wall_top + rise
        rib = (
            cq.Workplane("XZ")
            .polyline([(rob - 0.5, hd.thickness - 0.01), (rib_end, hd.thickness - 0.01), (x_wall_top, rib_top)])
            .close()
            .extrude(hd.rib_width / 2, both=True)
        )
        body = body.union(rib)

    body = body.cut(cavity(c, rb, extra=10).translate((0, 0, c.floor)))

    # rounded rim
    body = body.faces(">Z").edges().fillet(c.wall * 0.45)

    if hd.hang_hole > 0:
        body = body.cut(cq.Workplane("XY").center(tip_x, 0).circle(hd.hang_hole / 2).extrude(hd.thickness * 3, both=True))

    text = p.label.text or f"{p.volume:g} ml"
    if p.label.show and text.strip():
        label_start = rib_end + 2
        label_end = tip_x - (hd.hang_hole / 2 + 3 if hd.hang_hole > 0 else 0)
        emboss = (
            cq.Workplane("XY")
            .workplane(offset=hd.thickness - 0.01)
            .center((label_start + label_end) / 2, 0)
            .text(text, p.label.size, p.label.height + 0.01, kind="bold", halign="center", valign="center")
        )
        bb = emboss.val().BoundingBox()
        if bb.xmin < label_start or bb.xmax > label_end:
            raise ValueError(
                f"label {text!r} ({bb.xlen:.1f} mm) doesn't fit on the handle "
                f"({max(label_end - label_start, 0):.1f} mm free); make the handle longer or the font smaller"
            )
        body = body.union(emboss)

    if not body.val().isValid() or len(body.solids().vals()) != 1:
        raise RuntimeError("generated geometry is not a single valid solid")
    return body


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("volume", type=float, nargs="*", default=[60, 100], help="capacity in ml (default: 60 100)")
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                    help="override a parameter, e.g. cup.flare_angle=20 (repeatable)")
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--step", action="store_true", help="also export STEP")
    args = ap.parse_args()

    overrides: dict = {}
    for item in args.set:
        key, _, value = item.partition("=")
        *parents, leaf = key.split(".")
        target = overrides
        for part in parents:
            target = target.setdefault(part, {})
        target[leaf] = value

    args.out.mkdir(parents=True, exist_ok=True)
    for v in args.volume:
        params = Params.model_validate({**overrides, "volume": v})
        body = build(params)
        stem = args.out / f"measuring-scoop-{v:g}ml"
        cq.exporters.export(body, f"{stem}.stl", tolerance=0.02, angularTolerance=0.1)
        if args.step:
            cq.exporters.export(body, f"{stem}.step")
        rb = solve_bottom_radius(params.cup, v)
        rt, h = cavity_dims(params.cup, rb)
        print(f"{stem}.stl: {cavity(params.cup, rb).val().Volume() / 1000:.2f} ml, "
              f"inner {2 * rb:.1f} -> {2 * rt:.1f} mm diameter, {h:.1f} mm deep")
