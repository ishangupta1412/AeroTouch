# AeroTouch

<div align="center">

### Autonomous Dual-Hand Spatial Operating Layer
*Sub-millisecond touchless computer control powered by adaptive 1€ jitter filtering, velocity deadband noise gating, bimanual gesture chording, few-shot custom gesture learning, and local Qwen background kinematic tuning.*

<br/>

<p align="center">
  <img src="https://skillicons.dev/icons?i=python,opencv" alt="AeroTouch Core Tech Stack" />
</p>

[**Source Code**](https://github.com/ishangupta1412/AeroTouch) &nbsp;•&nbsp; 
[**System Architecture**](#system-architecture) &nbsp;•&nbsp; 
[**Gesture Controls**](#bimanual-gesture-chording-matrix) &nbsp;•&nbsp; 
[**MIT License**](./LICENSE)

<br/>

`Python 3.12` &nbsp;•&nbsp; 
`MediaPipe Tasks 3D Hands` &nbsp;•&nbsp; 
`Velocity Deadband Gate` &nbsp;•&nbsp; 
`1€ Dynamic Filter` &nbsp;•&nbsp; 
`Few-Shot Custom Poses` &nbsp;•&nbsp; 
`Ollama Qwen 2.5 Coach` &nbsp;•&nbsp; 
`Win32 Ctypes Kernel`

</div>

---

<div align="center">

![AeroTouch Real-Time Kinematics Demo](./assets/aerotouch_demo.gif)

*Real-time spatial optical tracking · Dynamic Deadband Noise Gate · Multi-Frame Click Confirmation*

</div>

---

## The Core Philosophy: Why Traditional Gesture Control Fails

Most open-source virtual mice and gesture-control experiments suffer from three critical engineering flaws:

1. **The Resting Muscle Tremor Problem**: Simple smoothing filters fail when the hand tries to hold still; physiological micro-tremors cause continuous cursor vibration and jitter.
2. **The Ghost-Click Defect**: Single-frame thresholding causes accidental, phantom clicks whenever the camera captures a noisy landmark frame.
3. **The Blocking Sleep Freeze**: Naive scripts use `time.sleep()` on click triggers to debounce, freezing the cursor and breaking user interaction continuity.

**AeroTouch** solves these challenges through a multi-stage architecture:
- **Dynamic Velocity Deadband Gate**: Locks the cursor completely still when hand movement is below human tremor thresholds (< 4.8 px).
- **Multi-Frame Temporal Confirmation**: Enforces 2 consecutive qualifying frames before firing clicks, eradicating phantom triggers.
- **Dynamic Pointer Ballistics**: Automatically gears down micro-movements (< 0.003 normalized velocity) by 0.5x for pixel-level sniper precision on tiny buttons, and accelerates fast flicks (> 0.015 velocity) up to 2.2x to traverse multi-monitor setups effortlessly.
- **Two-Finger Kinetic Scroll**: Trackpad-grade vertical scrolling with exponential moving average and momentum friction decay (0.85x per frame) for buttery-smooth page deceleration.
- **4-Way Spatial Window Snapping**: Left fist modifier combined with Right hand directional pinch provides instant 4-way window management (`Win + Up` maximize, `Win + Down` minimize, `Win + Left` snap left, `Win + Right` snap right).
- **Few-Shot Custom Gesture Learning**: Personalize new gestures in seconds with as few as 5-10 frames, mapped to hotkeys, media controls, or system actions via fast cosine similarity prototype matching (< 0.02ms).
- **Native Windows System Tray Daemon**: Runs quietly in the notification area with full context menu support (Pause/Resume, Recalibrate, Cortex Optimization, Toggle Preview, Exit) and native balloon/toast notifications.
- **Continuous 1-Euro Frequency Modulation**: Modulates filter cutoff dynamically with movement velocity ($\beta = 0.015$ calibrated for normalized spatial coordinates).
- **Background Kinematic Self-Tuning (Local Qwen)**: Analyzes session telemetry (pinch distance distribution, tremor variance) and auto-tunes parameters to fit individual hand geometry.
- **Ambient Floating Orb & Dynamic Island**: Minimal, borderless indicators that reflect tracking status and click events without obstructing the screen.

<div align="center">

<img src="./assets/floating_orb.gif" alt="Ambient Floating Orb" width="120" />

*Ambient glass orb with reactive state illumination*

</div>

---

## System Architecture

```
                    ┌──────────────────────────────┐
                    │ 60 FPS Native Webcam Feed    │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ 1. Vision Core: Dual-Hand 3D Landmark Extractor                  │
│ • Simultaneous 42 3D landmark extraction (MediaPipe Tasks Vision)│
│ • 3D rotation-invariant chirality (scalar triple product)        │
│ • Horizontal wrist-coordinate dual-hand disambiguation           │
│ • Scale normalization: 3D Euclidean / Wrist-to-MCP anchor        │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. Signal Engine: PrecisionSpatialFilter2D & PointerBallistics   │
│ • Spatial Noise Gate: Tremor < deadband threshold is 100% frozen │
│ • 1€ Adaptive Dynamic Filter: fc = min_cutoff + β|edx|           │
│ • Pointer Ballistics: Sniper precision (0.5x) to flick (2.2x)    │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. Interaction Engine: Bimanual Multi-Frame Confirmation FSM     │
│ • Left Hand = System Modifier (Fist = Snap, 3-Finger = Desktop)  │
│ • Right Hand = Continuous Pointer, Pinch Trigger & Kinetic Scroll│
│ • Multi-Frame Streak (confirm_frames = 2) kills ghost clicks     │
│ • Wide Hysteresis Gap (0.28 pinch / 0.38 release, 200ms debounce)│
│ • Few-Shot Custom Engine: Cosine prototype classifier (<0.02ms)  │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ 4. Execution Bridge: Direct user32.dll Win32 Input Synthesis     │
│ • Native user32.mouse_event / keybd_event (64-bit safe)          │
│ • Direct SetCursorPos integration (sub-millisecond latency)      │
│ • Native Shell_NotifyIcon system tray daemon integration         │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│ 5. Autonomous Cortex: Local Qwen Background Kinematic Coach      │
│ • Per-session telemetry recording (data/sessions/)               │
│ • Post-session analysis via local Ollama (aerotouch-qwen:latest) │
│ • Auto-tunes thresholds & writes to data/user_profile.json       │
└──────────────────────────────────────────────────────────────────┘
```

---

## Bimanual Gesture Chording Matrix

| Operational Mode | Left Hand (System Modifier) | Right Hand (Action Trigger) | Operating System Action |
| :--- | :--- | :--- | :--- |
| **Precision Mouse** | Resting / Out of frame | Index Tip Pointer | 60 FPS smoothed cursor with Dynamic Ballistics (Sniper Precision Mode) |
| **Intentional Click** | Resting / Out of frame | Index Tip + Thumb Pinch | Multi-frame confirmed Left Click (`VK_LBUTTON`) |
| **Context Menu** | Resting / Out of frame | Middle Tip + Thumb Pinch | Native Right Click (`VK_RBUTTON`) |
| **Kinetic Scroll** | Resting / Out of frame | Parallel Index + Middle Fingers | macOS-grade kinetic scrolling with momentum friction decay (`WHEEL`) |
| **Spatial Window Drag** | Resting / Out of frame | Closed Fist (Hold & Move) | Grabs foreground window in 3D, follows hand delta; release fist to drop |
| **Continuous Audio/Volume** | Two-Finger Peace Sign (`V`) | Variable Thumb-Index Pinch | Smooth real-time volume slider (0% to 100% via direct Core Audio) |
| **Gesture Sleep / Lock** | 🤙 Shaka (Hold 0.6s) | Either Hand | **Pauses/Resumes AeroTouch**: completely freezes spatial inputs so you can move hands freely |
| **4-Way Window Snapping** | Closed Fist (Grab active app) | Pinch & Move Up/Down/Left/Right | Full snapping matrix: Left (`Win+Left`), Right (`Win+Right`), Maximize (`Win+Up`), Minimize (`Win+Down`) |
| **Virtual Desktop Flip**| Three Fingers Extended | Index Pinch | Switch to next Virtual Desktop (`Win + Ctrl + Right`) |
| **Custom Few-Shot Pose** | Resting / Out of frame | User-Trained Custom Hand Pose | Custom hotkey, media play/pause, volume mute, or screenshot |
| **Emergency Desktop** | Open Palm Forward | Crossed Wrists | Minimize all windows / Show Desktop (`Win + D`) |

---

## Project Structure

```
AeroTouch/
├── src/                          # Core Python Engine
│   ├── core/
│   │   ├── one_euro_filter.py    # 1€ dynamic filter + Velocity Deadband Noise Gate
│   │   ├── calibrator.py         # Ergonomic perspective mapper & Pointer Ballistics engine
│   │   ├── tracker.py            # MediaPipe Tasks 3D dual-hand vision engine with chirality invariant
│   │   └── orchestrator.py       # End-to-end spatial event coordinator & profile loader
│   │
│   ├── gestures/
│   │   ├── engine.py             # Scale-invariant geometry & Multi-Frame Confirmation FSM
│   │   ├── few_shot_engine.py    # Prototype embedding & cosine similarity inference (<0.02ms)
│   │   ├── train_custom.py       # Custom gesture CLI trainer and registry
│   │   ├── micro_classifier.py   # 64x32 ReLU MLP neural classifier (0.08ms latency)
│   │   └── train_micro_mlp.py    # Fast self-calibration trainer
│   │
│   ├── cortex/
│   │   ├── session_analyst.py    # Qwen background kinematic parameter optimizer
│   │   ├── fine_tuner.py         # Ollama model compiler
│   │   └── dataset.py            # Telemetry synthetic benchmark generator
│   │
│   ├── telemetry/
│   │   └── session_logger.py     # Per-frame JSONL telemetry recorder
│   │
│   ├── os_bridge/
│   │   ├── win32_kernel.py       # Native user32.dll direct input synthesis & window hooks
│   │   ├── volume_control.py     # Continuous Core Audio & Brightness scalar controller
│   │   └── audio_feedback.py     # Non-blocking low-latency earcon audio feedback
│   │
│   ├── service/
│   │   ├── window_dragger.py     # Fist-drag spatial window repositioning state machine
│   │   ├── scroll_controller.py  # Two-finger kinetic scroll with momentum decay
│   │   ├── hotkey_daemon.py      # Win32 RegisterHotKey daemon (Ctrl + Alt + A)
│   │   └── setup_hotkey.py       # Desktop & Start Menu shortcut registrar
│   │
│   ├── ui/
│   │   ├── dynamic_island.py     # Top-center Apple-grade morphing Dynamic Island overlay
│   │   ├── hud.py                # Dual-hand 60 FPS visual HUD & live dataset recorder
│   │   ├── floating_orb.py       # Gemini Live style ambient floating glass orb
│   │   └── tray.py               # Native Windows Shell_NotifyIcon background tray daemon
│   │
│   └── main.py                   # 60 FPS real-time execution loop
│
├── assets/                       # Visual assets & diagrams
│   ├── aerotouch_demo.gif        # Real-time tracking & deadband demonstration GIF
│   └── floating_orb.gif          # Ambient breathing glass orb animation GIF
│
├── tests/                        # Automated Verification Suite (77/77 Passing)
│   ├── test_filter.py            # Tremor damping & deadband noise gate verification
│   ├── test_bimanual.py          # Multi-frame confirmation & debounce validation
│   ├── test_orchestrator.py      # End-to-end spatial pipeline & window snap test
│   ├── test_ballistics.py        # Pointer ballistics & micro-precision curves
│   ├── test_scroll.py            # Two-finger kinetic scrolling & friction decay
│   ├── test_snap_matrix.py       # 4-way window snapping directional matrix
│   ├── test_tray.py              # Windows notification tray lifecycle & callbacks
│   ├── test_few_shot.py          # Few-shot custom gesture normalization & matching
│   ├── test_shaka_lock.py        # 🤙 Shaka gesture lock/sleep state machine tests
│   ├── test_dynamic_island.py    # Apple-grade Dynamic Island morphing geometry tests
│   ├── test_tracker.py           # Biomechanical palm normal & handedness validation
│   ├── test_hud.py               # Visual HUD rendering & dataset recorder tests
│   ├── test_window_dragger.py    # Fist window drag & geometry delta tests
│   ├── test_volume_control.py    # Continuous audio/brightness scalar & deadband tests
│   ├── test_telemetry.py         # Telemetry logging & Qwen JSON parsing tests
│   ├── test_calibrator.py        # Screen corner reachability verification
│   ├── test_kernel.py            # Hardware resolution & keycode tests
│   ├── test_floating_orb.py      # Ambient UI state machine test
│   └── test_micro_classifier.py  # MLP inference benchmark (< 0.1ms)
│
├── models/
│   └── aerotouch-qwen/           # Custom Ollama Modelfile for kinematic optimization
│
├── config.toml                   # Intuitive user-facing threshold & sensitivity config
├── main.py                       # Root launcher (python main.py)
├── Start_AeroTouch.bat           # 1-Click launcher
├── Start_Floating_Orb.bat        # 1-Click launcher with Ambient Floating Orb
├── Start_Hotkey_Listener.bat     # Background daemon for Ctrl+Alt+A toggle
├── requirements.txt              # Production dependency manifest
└── LICENSE                       # MIT License
```

---

## Local Development & Setup

### Core Python Engine

```bash
# Clone repository
git clone https://github.com/ishangupta1412/AeroTouch.git
cd AeroTouch

# Install Python dependencies
pip install -r requirements.txt

# Run automated verification suite (77/77 tests pass)
python -m unittest discover -s tests -p "test_*.py" -v

# Launch AeroTouch spatial operating layer with Live Dynamic Island & Visual Studio HUD
python main.py

# Launch in background system tray mode (quietly in Windows notification bar)
python main.py --tray

# Press 'r' anytime during runtime to record live gesture training samples
# Hold 🤙 Shaka (thumb+pinky) for 0.6s to pause/resume AeroTouch anytime
# Or launch with ambient floating orb overlay
python main.py --orb
```

### Few-Shot Custom Gesture Training

Train custom hand poses in seconds using recorded samples:

```bash
# 1. List registered custom gestures
python -m src.gestures.train_custom --list

# 2. Learn a custom gesture from a recorded session
python -m src.gestures.train_custom --learn data/recorded_gestures/gesture_unlabeled_sample.jsonl --name THUMBS_UP --action MEDIA_PLAY_PAUSE

# 3. Bind to custom hotkeys (e.g., Ctrl+Shift+S)
python -m src.gestures.train_custom --learn data/recorded_gestures/sample2.jsonl --name SNIP_TOOL --action HOTKEY --param "win+shift+s"
```

---

## Engineering Verification Loop

AeroTouch includes a deterministic test suite verifying mathematical correctness without requiring hardware peripherals during continuous integration:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
# Ran 77 tests in 1.385s
# OK
# [Hardware Detected]: Display Resolution = 1920x1080
# [Micro-MLP Benchmark]: 0.074 ms per prediction (13428 FPS capability)
```

---

## Star History

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=ishangupta1412/AeroTouch&type=Date)](https://star-history.com/#ishangupta1412/AeroTouch&Date)

<sub>Live real-time telemetry chart tracked automatically via GitHub API</sub>

</div>

---

## License & Attribution

- **Architect & Author**: [Ishan Gupta](https://github.com/ishangupta1412) ([LinkedIn](https://www.linkedin.com/in/ishan14md) • [X](https://x.com/itsishan14))
- **License**: [MIT License](./LICENSE)
