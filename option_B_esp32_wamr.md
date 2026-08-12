# Option B: Sandboxed Community Console — ESP32-S3 and WebAssembly (WAMR)

## 1. Project Overview

This variant builds a genuinely bare-metal handheld device (ESP32-S3, no operating system) that lets community members submit and run original homebrew games safely. Instead of OS-level isolation, security comes from **WebAssembly (WASM)**: submitted games are compiled to WASM modules and executed by WAMR (WebAssembly Micro Runtime), a lightweight runtime purpose-built for microcontrollers. Safety rests on two mechanisms:

- **WASM's inherent memory safety** — a module cannot read or write memory outside its own sandboxed linear memory space by construction.
- **A capability system designed and implemented for this project** — the only way a WASM module can affect the outside world (draw to the display, play a sound, read its own save data) is through a small, explicit set of host functions registered by the firmware. Anything not explicitly exposed is structurally unreachable, not merely disallowed by policy.

## 2. Where the Gap Is

WebAssembly sandboxing on constrained microcontrollers is an established but genuinely current technique, and — importantly — it has not been applied to community gaming/entertainment hardware:

- **WAMR** (WebAssembly Micro Runtime, an Intel-led project) is the standard runtime for running sandboxed WASM modules on microcontroller-class hardware, supporting chips including the ESP32 family, nRF5x, and STM32.
- Recent academic work (2025-2026) directly evaluates WASM's performance, memory footprint, and security tradeoffs on constrained boards — including the Raspberry Pi Pico, ESP32-C6, and nRF5340 — finding that while native C execution remains faster and more energy-efficient, WASM offers an acceptable tradeoff where portability and sandboxed security matter more than raw performance (*WebAssembly on Resource-Constrained IoT Devices: Performance, Efficiency, and Portability*, arXiv 2512.00035).
- **AkiraOS**, a Zephyr-based embedded OS project, runs sandboxed WASM applications on ESP32-S3, nRF5x, and STM32, using a "Capability Guard" where every application must declare its required capabilities in a manifest before being permitted to run — architecturally very close to what this project's capability system would implement.
- **TinyContainer**, recent research on container-runtime middleware for multi-tenant microcontrollers with built-in security, confirms this is an active academic research direction, not settled or legacy technology.
- Every application context found in this space is industrial or infrastructure-flavored: IoT gateways, industrial automation modules, automotive infotainment and connectivity layers, sensor calibration logic. No literature or existing project was found applying WASM-on-microcontroller sandboxing to community-shared gaming or entertainment hardware.

**Stated gap:** WASM-based sandboxing for untrusted third-party code on microcontrollers is real, current, and validated as a security technique — but its application to a personal, community-oriented handheld gaming device, protected by a purpose-built capability system, does not appear in the existing literature or hobbyist project space.

## 3. Architecture

```
ESP32-S3 (bare metal, no OS)
├── Firmware
│   ├── Hardware drivers (display, buttons, audio, storage)
│   ├── WAMR runtime (interpreter mode)
│   └── Capability layer — the only bridge between WASM and hardware
│       ├── draw_pixel(x, y, color)
│       ├── play_tone(frequency)
│       ├── read_button_state()
│       └── read_own_save_slot()
└── WASM game modules (loaded from SD card or over WiFi)
    └── Cannot reach anything not explicitly exposed above
```

## 4. Day-to-Day Work, by Phase

**Phase 1 — Hardware bring-up (weeks 1-3)**
Wire an SPI display, GPIO button matrix, and I2S audio DAC/amp to the ESP32-S3 (the same chip family as the RFID player project, giving a genuine head start). Get basic firmware running: read buttons, draw to screen, play a sound. Day-to-day work: wiring, datasheet reading, debounce logic, debugging the display driver chain.

**Phase 2 — WAMR integration (weeks 4-6)**
Cross-compile WAMR for the ESP32-S3 target and get the interpreter running inside the firmware. Compile a trivial "hello world" WASM module (from C or Rust targeting WASM), load it from flash or SD card, and confirm it executes correctly. Day-to-day work: build-toolchain configuration, reading WAMR's embedding API documentation, iterating on small working examples.

**Phase 3 — Capability system design (weeks 7-9), the project's core security contribution**
Design and implement the exact set of host functions a game module may call, and register these as the *only* bridge WAMR exposes to hardware. Write deliberately malicious test modules (attempting to call undeclared functions, attempting out-of-bounds memory access) and confirm they are structurally rejected, not merely well-behaved by convention. Day-to-day work: interface design, WAMR native function registration, adversarial self-testing — actively trying to break the sandbox.

**Phase 4 — Games, submission flow, and polish (weeks 10-12)**
Write or port 2-3 small original homebrew games as WASM modules, appropriately scoped to microcontroller memory budgets (simple 2D, Pong/Snake-tier). Build a submission flow (SD card is the simpler, lower-risk choice; WiFi upload is a stretch goal if the "community" angle needs to feel more real) and an on-device menu to browse and launch games. Day-to-day work: game logic, UI polish, demo rehearsal, documentation of the threat model.

## 5. Feasibility Assessment

| Factor | Assessment |
|---|---|
| Hardware bring-up | Low risk — same chip family as a prior successful project (RFID player) |
| WAMR toolchain integration | Moderate risk — mostly build-system and cross-compilation friction, well-documented |
| Capability system design | Moderate risk, high reward — original design work with no existing template to copy, but well-scoped and testable incrementally |
| Memory/resource budget | Real constraint — MCU-class WASM typically works in kilobytes, not gigabytes, meaningfully limiting game complexity compared to Option A |
| Overall 12-week fit | Feasible, with a gentler risk profile than Option A's eBPF phase, since WAMR integration failures tend to be build-time (loud) rather than kernel-level (silent) |

**Fallback plan:** if capability-system edge cases prove difficult, fall back to interpreter-only WAMR with a deliberately minimal capability set (fewer host functions, more conservative defaults) — slower but still safe, and an easier, less risky fallback than Option A's.

## 6. Honest Limitations

- WASM's sandbox is strong but not absolute: academic work has identified real memory-safety issues that can still occur within a WASM sandbox (e.g. buffer overflows in linear memory) if not carefully handled, and this should be stated explicitly as part of the threat model rather than implied away.
- Using WAMR's AOT or JIT compilation modes for performance can undermine WASM's own sandboxing guarantees, since compiled native code bypasses the interpreter's safety checks — this project should default to interpreter mode and state that tradeoff explicitly.
- Games are necessarily simpler than Option A's, constrained by microcontroller memory and processing budgets.
- The individual technique (WASM-on-microcontroller sandboxing) is established in current research; the contribution is its specific application to community gaming hardware, not the underlying sandboxing theory.

## 7. Sources Consulted

- WAMR (WebAssembly Micro Runtime) project documentation
- *WebAssembly on Resource-Constrained IoT Devices: Performance, Efficiency, and Portability* (arXiv 2512.00035)
- *Benchmarking WebAssembly for Embedded Systems* (ACM Transactions on Architecture and Code Optimization)
- AkiraOS — WASM Runtime for Microcontrollers (Hackster.io project documentation)
- *TinyContainer: Container Runtime Middleware Enabling Multi-tenant Microcontrollers with Built-in Security* (arXiv)
- *WebAssembly for Embedded Systems: A New Era of Cross-Platform Firmware*
- *Memory Safety Preservation for WebAssembly* (CISPA Helmholz Center / Stanford)
