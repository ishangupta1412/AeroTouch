"""
AeroTouch Micro-MLP Trainer & Self-Calibration CLI
Allows fast retraining and fine-tuning of the neural gesture classifier on custom hand geometry.
"""

import os
import sys
import time
from src.gestures.micro_classifier import MicroGestureClassifier, GESTURE_CLASSES


def train_gesture_model():
    print("=" * 65)
    print("      AEROTOUCH: NEURAL GESTURE CLASSIFIER CALIBRATOR     ")
    print("=" * 65)
    print("Target Architecture: Multi-Layer Perceptron (64x32 ReLU)")
    print(f"Supported Gesture Classes ({len(GESTURE_CLASSES)}):")
    for i, cls in enumerate(GESTURE_CLASSES):
        print(f"  {i}: {cls}")
    print("\nTraining synthetic scale-invariant geometry dataset...")

    start_time = time.perf_counter()
    clf = MicroGestureClassifier()
    clf.train_default_model()
    elapsed = (time.perf_counter() - start_time) * 1000

    print(f"[SUCCESS]: Gesture model trained and persisted in {elapsed:.1f} ms!")
    print(f"Artifact Location: {clf.model_path}")


if __name__ == "__main__":
    train_gesture_model()
