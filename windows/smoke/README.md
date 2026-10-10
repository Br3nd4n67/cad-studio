# Windows CAD engine proof

This is the first executable Windows milestone, not the CAD Studio desktop app.
It uses no coding agent and does not consume an agent plan. Run it in a disposable
project directory: `model.py` writes/overwrites known files under `./output/`.
Do not run this fixture inside a real CAD project.

## Tested on 2026-10-09

- Windows 11, build 26200, AMD64; Python 3.12.10 (64-bit).
- build123d 0.13.0, cadquery-ocp-novtk 8.0.1.1.0, lib3mf 2.5.0,
  matplotlib 3.11.2, numpy 2.5.3.
- Full resolved environment captured in `requirements-windows-py312.txt`.
  These are the versions tested on this machine, not a claim of compatibility
  across Python versions or CPU architectures.
- Both a normal folder and `Geometry test café` passed.

## Repeat with an isolated environment

Prerequisites: Windows x64, Python 3.12, and uv already installed. From the
repository root, run these separately in PowerShell. These commands use uv to
install packages into a local virtual environment without changing global Python.

```powershell
uv venv --python 3.12 --cache-dir .windows-work/cache .windows-work/venv
```

```powershell
uv pip sync --cache-dir .windows-work/cache --python .windows-work/venv/Scripts/python.exe windows/smoke/requirements-windows-py312.txt
```

```powershell
& ./windows/smoke/run.ps1 -Python .windows-work/venv/Scripts/python.exe
```

The runner creates a new unique project directory under `.windows-work/` for
each invocation. It exercises both plain and Unicode names, stops on a failing
Python exit code, and prints the location of the generated artifacts. No activation
script, admin privileges, or global execution-policy change is needed. If local
policy blocks this unsigned PowerShell runner, use the same Python interpreter to
run `model.py` manually from two new disposable directories instead.

## What is checked

The fixture is a 40 x 30 x 8 mm box with a centered 6 mm through-hole. The dimensions
are independent of any physical fastener tests discussed elsewhere.

- One valid solid, exact bounds and analytic volume: 9373.805328941535 mm³.
- STEP export followed by reimport, with valid-solid, volume and bounds checks.
- Binary STL structure, 520 triangles for the tested dependency versions,
  bounds and signed mesh volume within 0.1% of the analytic volume.
- Model and plate 3MF ZIP integrity, millimeter units, nonempty mesh and bounds.
- Nonempty SVG, PNG, PDF and manifest; SVG parses and raster/document headers match.
- A JSON verification record including interpreter, OS, dependencies and file sizes.

The drawing is a simple analytic dimensioned top view made with matplotlib. It is
not an implementation of the macOS app's full ISO drawing or PDF viewing features.
The single-part plate uses the same mesh already placed flat on Z=0. These checks
do not validate multipart colors, assembly transforms, slicing, physical printing,
agent permissions, the desktop renderer or installer behavior.

## Setup observations

The existing Python interpreter ran successfully. Python's `venv` created the
isolated interpreter, but its `ensurepip` step failed in the restricted execution
environment. The already-installed uv installed the packages into that interpreter
successfully with a workspace-local cache. `uv venv` is the repeatable setup above.
An initial `uv pip freeze` without an explicit cache directory failed; repeating it
with a workspace-local cache succeeded. Initial imports also printed a nonfatal
ezdxf cache-directory warning. Neither geometry run encountered a CAD DLL load error.
This is evidence from one development machine, not a clean-machine installer test.

Next milestone: the Windows process adapter, including streamed output, safe
argument handling, cancellation and owned child-process cleanup.
