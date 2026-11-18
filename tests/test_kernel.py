import unittest
from src.os_bridge.win32_kernel import Win32KernelBridge, VirtualKey


class TestWin32KernelBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = Win32KernelBridge()

    def test_screen_resolution_retrieval(self):
        w, h = self.bridge.get_screen_resolution()
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)
        print(f"\n[Hardware Detected]: Display Resolution = {w}x{h}")

    def test_virtual_keys_defined(self):
        self.assertEqual(VirtualKey.VK_LWIN, 0x5B)
        self.assertEqual(VirtualKey.VK_D, 0x44)
        self.assertEqual(VirtualKey.VK_RETURN, 0x0D)


if __name__ == '__main__':
    unittest.main()
