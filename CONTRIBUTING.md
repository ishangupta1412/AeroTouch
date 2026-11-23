# Contributing to AeroTouch

Thank you for your interest in contributing to AeroTouch. This document outlines guidelines and development standards for maintaining code quality across our spatial operating layer.

## Development Principles

1. **Sub-Millisecond Latency Budget**: Any processing step added to the frame loop must operate within a strict runtime budget. Profiling is required for all computer vision or signal processing additions.
2. **Deterministic Kinematics**: Spatial filters and kinematic constraints must be mathematically deterministic and tested against synthetic trajectories.
3. **No Regressions**: All existing unit test suites must pass before submitting contributions.

## Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ishangupta1412/AeroTouch.git
   cd AeroTouch
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the automated test suite:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```

## Pull Request Guidelines

- Branch names should be descriptive (e.g., `feat/adaptive-filter`, `fix/cursor-drift`).
- Every new feature must include corresponding automated unit tests under `tests/`.
- Ensure code follows standard PEP 8 naming conventions and includes comprehensive type annotations.
- Include before-and-after performance metrics where applicable.
