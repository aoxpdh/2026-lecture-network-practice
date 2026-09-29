"""Additional boundary checks; the supplied grading harness is unchanged."""
import unittest

from task1_forward import ForwardingTable, network_range, parse_cidr


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


if __name__ == "__main__":
    unittest.main()
