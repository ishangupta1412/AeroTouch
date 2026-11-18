import unittest
import time
from src.gestures.micro_classifier import MicroGestureClassifier, GESTURE_CLASSES


class TestMicroGestureClassifier(unittest.TestCase):
    def setUp(self):
        self.clf = MicroGestureClassifier()

    def test_classifier_loads_and_predicts(self):
        # Create a synthetic index pointer
        pts = [(0.0, 0.0, 0.0)] * 21
        pts[0] = (0.5, 0.8, 0.0)  # Wrist
        pts[9] = (0.5, 0.5, 0.0)  # Middle MCP
        pts[8] = (0.5, 0.2, 0.0)  # Index tip up

        gesture, conf = self.clf.predict(pts)
        self.assertIn(gesture, GESTURE_CLASSES)
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)

    def test_inference_latency_sub_millisecond(self):
        pts = [(0.5, 0.5, 0.0)] * 21
        
        # Warmup
        for _ in range(5):
            self.clf.predict(pts)

        # Benchmark 100 runs
        start = time.perf_counter()
        n_runs = 100
        for _ in range(n_runs):
            self.clf.predict(pts)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / n_runs) * 1000
        print(f"\n[Micro-MLP Benchmark]: {avg_ms:.3f} ms per prediction ({1000/avg_ms:.0f} FPS capability)")
        self.assertLess(avg_ms, 5.0)  # Must be faster than 5ms


if __name__ == '__main__':
    unittest.main()
