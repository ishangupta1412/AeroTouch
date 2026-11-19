"""
AeroTouch Custom Gesture Training CLI
Command-line utility to inspect, train, and bind custom gestures using the Few-Shot Engine.
"""

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.gestures.few_shot_engine import FewShotGestureEngine


def main():
    parser = argparse.ArgumentParser(description="AeroTouch Custom Gesture Trainer")
    parser.add_argument("--list", action="store_true", help="List all registered custom gestures")
    parser.add_argument("--learn", type=str, help="Path to JSONL recording file from GestureRecorder ('R' key)")
    parser.add_argument("--name", type=str, help="Name of the custom gesture")
    parser.add_argument("--hand", type=str, default="right", choices=["right", "left"], help="Hand to extract (right or left)")
    parser.add_argument("--action", type=str, default="HOTKEY", help="Action to trigger (HOTKEY, MEDIA_PLAY_PAUSE, VOLUME_MUTE, SCREENSHOT, TASK_VIEW)")
    parser.add_argument("--param", type=str, default=None, help="Action parameter (e.g. 'ctrl+c' for HOTKEY)")
    parser.add_argument("--threshold", type=float, default=0.88, help="Cosine similarity threshold (default: 0.88)")
    parser.add_argument("--remove", type=str, help="Remove a registered custom gesture by name")

    args = parser.parse_args()
    engine = FewShotGestureEngine()

    if args.list:
        gestures = engine.list_gestures()
        print("\n" + "=" * 65)
        print("          AEROTOUCH: REGISTERED CUSTOM GESTURES            ")
        print("=" * 65)
        if not gestures:
            print("No custom gestures registered yet.")
            print("Tip: Record a gesture in HUD (press 'R'), then run:")
            print("  python -m src.gestures.train_custom --learn <file.jsonl> --name MY_GESTURE --action MEDIA_PLAY_PAUSE\n")
            return

        for g in gestures:
            print(f" * [{g['name']}]")
            print(f"     Samples:   {g['samples']} frames")
            print(f"     Threshold: {g['threshold']:.2f}")
            print(f"     Action:    {g['action']} (Param: {g['action_param']})")
        print("=" * 65 + "\n")
        return

    if args.remove:
        if engine.remove_gesture(args.remove):
            print(f"[SUCCESS]: Custom gesture '{args.remove}' removed.")
        else:
            print(f"[ERROR]: Custom gesture '{args.remove}' not found.")
        return

    if args.learn:
        if not args.name:
            print("[ERROR]: Must specify --name when registering a custom gesture.")
            return

        success = engine.register_gesture_from_jsonl(
            name=args.name,
            jsonl_path=args.learn,
            hand_side=args.hand,
            action=args.action,
            action_param=args.param,
            similarity_threshold=args.threshold
        )
        if success:
            print(f"\n[SUCCESS]: Gesture '{args.name}' registered into AeroTouch!")
            print(f"Action: {args.action} | Threshold: {args.threshold}\n")
        else:
            print(f"\n[FAILED]: Could not learn gesture '{args.name}'. Check JSONL file path and frames.\n")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
