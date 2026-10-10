"""Windows CAD engine proof. Run in a disposable project directory.

No agent, network, or global configuration is used by this script.
Outputs are written to ./output, matching the CAD Studio project convention.
"""

import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / ".matplotlib"))

from build123d import Align, Box, Cylinder, Mesher, export_step, export_stl, import_step
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

WIDTH = 40.0  # mm, X dimension
DEPTH = 30.0  # mm, Y dimension
HEIGHT = 8.0  # mm, Z dimension
HOLE_DIAMETER = 6.0  # mm, centered through-hole (not a fastener-fit test)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def dimensions(shape):
    size = shape.bounding_box().size
    return [size.X, size.Y, size.Z]


def build():
    alignment = (Align.CENTER, Align.CENTER, Align.MIN)
    solid = Box(WIDTH, DEPTH, HEIGHT, align=alignment) - Cylinder(
        HOLE_DIAMETER / 2, HEIGHT, align=alignment
    )
    solid.label = "Windows CAD smoke test"
    return solid


def drawing(destination):
    # Dimensioned top view of this analytic fixture, not full ISO drawing parity.
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.add_patch(Rectangle((-WIDTH / 2, -DEPTH / 2), WIDTH, DEPTH,
                           fill=False, linewidth=1.8))
    ax.add_patch(Circle((0, 0), HOLE_DIAMETER / 2, fill=False, linewidth=1.5))
    ax.axhline(0, color="gray", linestyle="-.", linewidth=0.6)
    ax.axvline(0, color="gray", linestyle="-.", linewidth=0.6)
    ax.annotate("", (-WIDTH / 2, -DEPTH / 2 - 4),
                (WIDTH / 2, -DEPTH / 2 - 4), arrowprops={"arrowstyle": "<->"})
    ax.text(0, -DEPTH / 2 - 6, f"{WIDTH:g} mm", ha="center")
    ax.annotate(f"Hole diameter {HOLE_DIAMETER:g} mm", (HOLE_DIAMETER / 2, 0),
                (7, 7), arrowprops={"arrowstyle": "->"})
    ax.set(xlim=(-27, 27), ylim=(-24, 23), aspect="equal", xlabel="X (mm)",
           ylabel="Y (mm)", title=f"Windows CAD proof | {WIDTH:g} x {DEPTH:g} x {HEIGHT:g} mm")
    fig.tight_layout()
    for extension in ("svg", "png", "pdf"):
        fig.savefig(destination / f"schematic.{extension}", dpi=160)
    plt.close(fig)


def verify_stl(path):
    raw = path.read_bytes()
    require(len(raw) >= 84, "STL header is missing")
    count = struct.unpack_from("<I", raw, 80)[0]
    require(count > 0 and len(raw) == 84 + 50 * count, "Invalid binary STL length")
    vertices = []
    volume = 0.0
    for offset in range(84, len(raw), 50):
        values = struct.unpack_from("<12fH", raw, offset)
        a, b, c = values[3:6], values[6:9], values[9:12]
        vertices.extend((a, b, c))
        cross = (b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0])
        volume += sum(a[i] * cross[i] for i in range(3)) / 6
    bounds = [max(v[i] for v in vertices) - min(v[i] for v in vertices) for i in range(3)]
    require(all(math.isclose(a, b, abs_tol=1e-4) for a, b in zip(bounds, (WIDTH, DEPTH, HEIGHT))),
            "STL bounds changed")
    expected = (WIDTH * DEPTH - math.pi * (HOLE_DIAMETER / 2)**2) * HEIGHT
    require(math.isclose(abs(volume), expected, rel_tol=0.001), "STL volume mismatch")
    return {"triangles": count, "bounds_mm": bounds, "volume_mm3": abs(volume)}


def verify_three_mf(path):
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, "3MF archive CRC failure")
        model = ET.fromstring(archive.read("3D/3dmodel.model"))
    require(model.attrib.get("unit", "millimeter") == "millimeter", "3MF units changed")
    vertices = model.findall(".//m:vertex", ns)
    triangles = model.findall(".//m:triangle", ns)
    require(vertices and triangles, "3MF mesh is empty")
    points = [tuple(float(v.attrib[axis]) for axis in ("x", "y", "z")) for v in vertices]
    require(all(math.isfinite(value) for point in points for value in point), "3MF nonfinite vertex")
    bounds = [max(v[i] for v in points) - min(v[i] for v in points) for i in range(3)]
    require(all(math.isclose(a, b, abs_tol=1e-4) for a, b in zip(bounds, (WIDTH, DEPTH, HEIGHT))),
            "3MF bounds changed")
    return {"vertices": len(vertices), "triangles": len(triangles), "bounds_mm": bounds}


def main():
    output = Path("output")
    output.mkdir(exist_ok=True)
    solid = build()
    expected = (WIDTH * DEPTH - math.pi * (HOLE_DIAMETER / 2)**2) * HEIGHT
    require(solid.is_valid and len(solid.solids()) == 1, "Expected one valid solid")
    require(math.isclose(solid.volume, expected, rel_tol=1e-8), "Analytic volume mismatch")
    require(all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(dimensions(solid), (WIDTH, DEPTH, HEIGHT))),
            "Solid dimensions changed")
    export_step(solid, output / "model.step")
    export_stl(solid, output / "model.stl")
    mesher = Mesher()
    mesher.add_shape(solid)
    mesher.write(output / "model.3mf")
    # Single-part plate: this fixture is already flat on Z=0.
    mesher.write(output / "plate.3mf")
    drawing(output)
    manifest = {"bounding_box": dict(zip(("x", "y", "z"), dimensions(solid))),
                "parameters": {"width": WIDTH, "depth": DEPTH, "height": HEIGHT,
                               "hole_diameter": HOLE_DIAMETER},
                "warnings": [], "drawings": [{"file": "schematic.svg", "title": "Top view"}]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    restored = import_step(output / "model.step")
    require(restored.is_valid and len(restored.solids()) == 1, "STEP round-trip invalid")
    require(math.isclose(restored.volume, expected, rel_tol=1e-8), "STEP round-trip volume mismatch")
    require(all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(dimensions(restored), (WIDTH, DEPTH, HEIGHT))),
            "STEP round-trip dimensions changed")
    report = {"status": "passed", "python": sys.version, "executable": sys.executable,
              "platform": platform.platform(), "machine": platform.machine(),
              "project_directory": str(Path.cwd()),
              "versions": {name: importlib.metadata.version(name) for name in
                           ("build123d", "cadquery-ocp-novtk", "lib3mf", "matplotlib", "numpy")},
              "valid_solid": True, "volume_mm3": solid.volume, "expected_volume_mm3": expected,
              "step_round_trip": True, "stl": verify_stl(output / "model.stl"),
              "three_mf": verify_three_mf(output / "model.3mf"),
              "plate_three_mf": verify_three_mf(output / "plate.3mf")}
    files = ("model.step", "model.stl", "model.3mf", "plate.3mf", "schematic.svg",
             "schematic.png", "schematic.pdf", "manifest.json")
    report["files"] = {name: (output / name).stat().st_size for name in files}
    require(all(report["files"].values()), "An output file is empty")
    ET.parse(output / "schematic.svg")
    require((output / "schematic.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "Invalid PNG")
    require((output / "schematic.pdf").read_bytes().startswith(b"%PDF-"), "Invalid PDF")
    (output / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
