"""Additional boundary checks; the supplied grading harness is unchanged."""
import unittest
import random

from task1_forward import ForwardingTable, network_range, parse_cidr
from task3_lpm import LinearTable, YourTable


class SubnetTests(unittest.TestCase):
    def test_invalid_cidr(self):
        for cidr in ("1.2.3.0/-1", "1.2.3.0/33", "163.152.6.5/24",
                     "256.0.0.0/8", "1.2.3/24", "a.0.0.0/8", "1.2.3.4"):
            with self.subTest(cidr=cidr), self.assertRaises(ValueError):
                parse_cidr(cidr)

    def test_boundaries(self):
        self.assertEqual(parse_cidr("0.0.0.0/0"), (0, 0))
        self.assertEqual(network_range("192.0.2.0/31"),
                         ("192.0.2.0", "192.0.2.1", "192.0.2.1"))
        self.assertEqual(network_range("192.0.2.7/32"), ("192.0.2.7",) * 3)
        self.assertEqual(network_range("192.0.2.0/30"),
                         ("192.0.2.1", "192.0.2.2", "192.0.2.3"))

    def test_ties_and_default(self):
        table = ForwardingTable()
        self.assertIsNone(table.lookup("192.0.2.1"))
        table.add("192.0.2.0/24", "first")
        table.add("192.0.2.0/24", "second")
        table.add("0.0.0.0/0", "default")
        self.assertEqual(table.lookup("192.0.2.1"), "first")
        self.assertEqual(table.lookup("203.0.113.1"), "default")
        table.add("192.0.2.1/32", "host")
        self.assertEqual(table.lookup("192.0.2.1"), "host")


class FastTableTests(unittest.TestCase):
    def test_all_lengths_ties_and_incremental_add(self):
        slow, fast = LinearTable(), YourTable()
        self.assertIsNone(fast.lookup(0))
        rng = random.Random(5)
        for length in range(33):
            mask = (0xFFFFFFFF << (32 - length)) & 0xFFFFFFFF
            network = rng.getrandbits(32) & mask
            for hop in (None if length == 32 else str(length), "duplicate"):
                slow.add(network, length, hop)
                fast.add(network, length, hop)
            for address in [network, network | (0xFFFFFFFF ^ mask),
                            *[rng.getrandbits(32) for _ in range(100)]]:
                self.assertEqual(fast.lookup(address), slow.lookup(address))


if __name__ == "__main__":
    unittest.main()
