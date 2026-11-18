"""
AeroTouch Continual Learning & Model Compiler
Recompiles the local Ollama Qwen model with updated kinematic system prompts and instructions.
"""

import os
import subprocess


def recompile_aerotouch_qwen():
    """Recompiles aerotouch-qwen Ollama model with latest Modelfile."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    modelfile = os.path.join(base_dir, "models", "aerotouch-qwen", "Modelfile")

    print(f"[Cortex Compiler]: Recompiling aerotouch-qwen from {modelfile}...")
    try:
        res = subprocess.run(
            ["ollama", "create", "aerotouch-qwen", "-f", modelfile],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            print("[SUCCESS]: aerotouch-qwen kinematic model updated.")
            return True
        else:
            print(f"[ERROR]: Ollama compilation failed: {res.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR]: Subprocess execution error: {e}")
        return False


if __name__ == "__main__":
    recompile_aerotouch_qwen()
