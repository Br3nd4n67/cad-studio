# Windows port plan

Status: first Windows geometry milestone passed, 2026-10-09. See [the repeatable test](../windows/smoke/README.md). No Windows desktop executable, installer, or working GUI exists in this branch. The macOS application source remains unchanged.

Fork: https://github.com/Br3nd4n67/cad-studio
Upstream inspected: filippofinke/cad-studio at a7c4c477e135340eb1d653e739a1ecdb00d9f4ab.
Keep upstream copyright and MIT license. All port work belongs in this fork. Leave main aligned with the inspected source while developing on a separate branch. Do not run release or Pages workflows as a side effect of port development.

## Findings from the source

This requires a new Windows application host and renderer, not just a different build script. Installing Swift on Windows does not supply the Apple frameworks used here.

| Area | Source evidence | Work needed on Windows |
| --- | --- | --- |
| App and layout | `CADStudio/App/*.swift`, `Shared/PaneSplitViewController.swift`, SwiftUI and AppKit | Replace windows, menus, split panels, settings, file dialogs, clipboard and drag/drop. |
| 3D viewport | `Viewer3D/ModelViewer.swift` uses RealityKit; `CameraInputView.swift` uses AppKit; mesh code uses simd | Replace renderer and camera input; preserve millimeters, part colors, transforms, selection and bounds. Port mesh math and parsers with fixtures. |
| Drawings | `Schematic/SVGWebView.swift`, `SchematicPane.swift`, `Project/Project.swift` use WebKit/PDFKit and macOS Preview | Replace SVG/PDF display, page handling and default-app launch. |
| Python setup | `Python/PythonEnvironment.swift` uses application support storage and `venv/bin/python`, searches python3.10 through python3.13, prefers uv with Python 3.12 | Use a dedicated environment under Windows local app data and `venv/Scripts/python.exe`; probe compatible interpreters explicitly, including the py launcher. Validate dependency wheels and DLL loading on target architecture. |
| Tool discovery | `Shared/ShellEnvironment.swift`, `Agent/AgentLocator.swift` use `/bin/zsh -lc`, colon-separated PATH and Homebrew/Unix paths | Use Windows PATH/PATHEXT and an explicit executable override. Handle native executables and npm command shims separately. Never concatenate project names or prompts into shell commands. |
| Process lifecycle | `Shared/ProcessRunner.swift` uses POSIX signals, proc_pidinfo and macOS application termination APIs | Implement concurrent stdout/stderr streaming, UTF-8/CRLF parsing, cancellation and process-tree cleanup using Windows process ownership. Do not terminate a process based only on a stale PID. |
| Agent permissions and prompts | `Agent/ClaudeRunner.swift`, `CodexRunner.swift`, `Resources/CADSystemPrompt.md` | Adapt shell-specific quoting, interpreter invocation and Restricted Bash rules. Preserve isolation intent; validate actual installed CLI flags and sandbox behavior before integrating. |
| File updates | `Shared/FileWatcher.swift` uses CoreServices FSEvents | Replace with a Windows watcher, debounce duplicate events and tolerate partially written output. |
| Archives and exports | `Viewer3D/ThreeMFParser.swift` invokes `/usr/bin/unzip`; `Project/Project.swift` invokes `/usr/bin/zip` | Use an archive library. Preserve 3MF units, components, transforms and materials; limit archive expansion and reject traversal paths. |
| Packaging and CI | `build.sh`, `CADStudio.xcodeproj`, `.github/workflows/ci.yml`, `release.yml`, `pages.yml` | Existing build is Xcode plus codesign/hdiutil and produces a DMG. Add a separate Windows build/test path later. Release and Pages remain outside this port-plan scope. |

## What can be carried forward

The stable boundary is the project directory and file formats, rather than the Apple UI classes. Reference `Project/ProjectFolder.swift`, `Project/Manifest.swift`, `Project/ProjectStore.swift`, `Project/VersionHistory.swift`, `Agent/StreamEvent.swift`, `Agent/CodexRunner.swift` and the CAD system prompt when defining compatibility.

Preserve `model.py`, `references/`, `output/` and `.cadstudio/` layout. Outputs include model.3mf, model.stl, model.step, plate.3mf, schematic.svg/.png/.pdf, numbered drawing sheets, manifest.json and optional animation.json. Preserve project/chat/version JSON keys and timestamp encoding after checking real fixtures. A restored file snapshot does not by itself guarantee the corresponding agent session is portable between operating systems.

The Python script/export contract, printing rules, agent event mapping and history behavior can be reused as specifications. Swift geometry and parser code will still need adaptation or translation if the new host uses another language. The `site/` directory is marketing material, not an existing browser-based CAD application.

## Proposed architecture to validate

Start with a local desktop host, an independently testable process/storage layer and a web-based viewer. One candidate is a .NET Windows host with WebView2 and a WebGL renderer. This is a design proposal, not a selected dependency stack or a verified compatibility claim; check current official documentation, licensing and deployment prerequisites before implementation. Keep backend operations behind narrow calls rather than giving web content arbitrary filesystem or shell access.

Define separate interfaces for platform paths, tool discovery, process running/cancellation, project storage, output watching, archive handling, and renderer updates. The first interface contracts should accept an executable plus argument list, a working directory and environment overrides. Preserve `MPLBACKEND=Agg` and `PYTHONUNBUFFERED=1` from `Python/ModelBuilder.swift`.

Scope the initial target to Windows 11 x64. ARM64 and broader OS compatibility require separate dependency and packaging validation. Do not assume CAD geometry wheels work merely because Python starts.

## Ordered implementation milestones

1. **Headless geometry proof.** In a new disposable project folder, create a dedicated Python 3.12 environment, install and record tested build123d/matplotlib/numpy versions, and run a hand-written box-with-hole model. Verify a valid solid, positive volume, expected dimensions and nonempty STEP/STL/3MF plus a simple drawing. Repeat under a path with spaces and Unicode. Record exact interpreter/package versions and DLL issues. No agent or paid generation is needed for this milestone.
2. **Windows process adapter.** Stream a fixture child process that emits split UTF-8 lines on stdout/stderr and creates a child of its own. Verify completion, errors, cancellation, no UI blocking, and cleanup only of owned processes. Resolve native agents and command shims without unsafe string interpolation.
3. **Project compatibility.** Capture disposable macOS-format fixtures. Read project/chat/manifest/version records; preserve unsupported fields. Back up before any migration or restore. Prove snapshot/restore survives restart and cannot escape its project directory.
4. **First desktop slice.** Open a folder, run its model.py through the dedicated interpreter, display an STL with orbit/zoom/pan, show SVG/PNG drawings and generation errors. Debounce output changes and retain the last good model during partial writes. This is a usable manual modeling milestone, not full feature parity.
5. **One agent integration.** Choose an installed, authenticated CLI after checking its current Windows documentation. Stream a bounded generation, persist chat, then generate a second version and restore the first. Test quoting and isolation; fail visibly if required safeguards are unsupported. Do not disable sandboxing to obtain a passing demo. Add the second provider after the first works.
6. **Richer parity.** Add 3MF part colors/transforms, plate view, parameter edits, PDFs, attachments and ZIP export. Then port measurements, sections, explode and animation behavior. Validate each against fixtures before claiming parity.
7. **Packaging.** Add Windows CI with deterministic geometry/fixture tests and a clean-machine install test. Produce a preview installer only after the above gates pass. Publishing, signing and releases need a separate explicit decision.

## Acceptance checks and known uncertainties

- Tool discovery must distinguish missing tools, missing authentication and process failure; tests should not spend an agent quota by default.
- Handle drive letters, spaces, Unicode, Windows reserved filenames, CRLF, long paths and file locks.
- Verify 3MF object hierarchy, transform ordering, color and unit conversion against known expected geometry; an STL-only viewer is not 3MF parity.
- Agent command permissions, shell behavior and sandbox support require live validation on the chosen CLI version. Do not claim security equivalence from matching flag names.
- Version restore must be reversible and preserve the pre-restore model, output and chat. Cross-OS agent session resume is an open question.
- A Windows build passing CI is not proof of interactive rendering, printer/slicer interoperability or a successful physical print.

## Work record

- 2026-10-09: Created the personal GitHub fork, copied main only, and inspected the source files listed above at the recorded SHA.
- 2026-10-09: Added this plan on windows-port-plan. No upstream edits or upstream pull request. No source-code port, dependency installation, agent generation, application build, installer, release or deployment performed.
- 2026-10-09: Completed milestone 1 on Windows 11 AMD64 with Python 3.12.10 and build123d 0.13.0. Validated solid dimensions/volume, STEP round-trip, STL structure/bounds/volume, 3MF archive/mesh/bounds/units, and simple drawing outputs in normal and space/Unicode paths. Added the fixture, runner and exact package versions under windows/smoke. See its README for limitations and setup observations.
- Next concrete task: milestone 2, Windows process streaming and owned child-process cleanup. Read this record and local CAD_STUDIO_WORK_NOTES.md before continuing.
