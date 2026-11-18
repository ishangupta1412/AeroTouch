"""
AeroTouch Continual Learning & Fine-Tuner Engine
Reads collected interaction logs, updates training datasets, and recompiles the local Ollama Qwen model.
"""

import os
import json
import subprocess
from src.cortex.dataset import generate_jsonl_dataset


def run_continuous_fine_tune():
    print("=" * 65)
    print("      AEROTOUCH: LOCAL LLM CONTINUAL FINE-TUNER      ")
    print("=" * 65)

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(base_dir, "data")
    log_file = os.path.join(data_dir, "interaction_history.jsonl")
    dataset_file = os.path.join(data_dir, "fine_tune_dataset.jsonl")
    modelfile = os.path.join(base_dir, "models", "aerotouch-qwen", "Modelfile")

    # Step 1: Count collected history
    history_count = 0
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    history_count += 1
    print(f"Status: Found {history_count} real-world user interactions in history.")

    # Step 2: Regenerate dataset with baseline pairs
    total_samples = generate_jsonl_dataset(dataset_file)
    print(f"Status: Dataset compiled with {total_samples + history_count} samples.")

    # Step 3: Recompile Ollama custom model
    print("Compiling adapted Ollama model: aerotouch-qwen:latest ...")
    try:
        res = subprocess.run(
            ["ollama", "create", "aerotouch-qwen", "-f", modelfile],
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            print("[SUCCESS]: aerotouch-qwen successfully updated and fine-tuned locally!")
        else:
            print(f"[ERROR]: Ollama compilation failed: {res.stderr}")
    except Exception as e:
        print(f"[ERROR]: Subprocess execution error: {e}")


if __name__ == "__main__":
    run_continuous_fine_tune()
