"""Extra tests with varied bytes; the original harness repeats a single byte."""
import random
import unittest

from task1_rdt import Receiver, Sender, UnreliableChannel


class ReliabilityTests(unittest.TestCase):
    def test_varied_payloads_and_channel_conditions(self):
        for seed, size, loss, dup, reorder in (
            (246, 2000, .1, .03, .1), (999, 2000, .1, .03, .1),
            (7, 2037, .25, .4, .8), (8, 1, .1, .03, .1),
            (9, 0, .1, .03, .1), (10, 256, 0, 0, 0),
        ):
            with self.subTest(seed=seed, size=size):
                rng = random.Random(seed)
                data = bytes(rng.getrandbits(8) for _ in range(size))
                up = UnreliableChannel(seed, loss, dup, reorder)
                down = UnreliableChannel(seed + 1, loss, dup, reorder)
                sender, receiver = Sender(up, down, data), Receiver(up, down)
                for _ in range(200000):
                    alive = sender.step()
                    receiver.step()
                    if not alive:
                        break
                else:
                    self.fail("sender did not terminate")
                self.assertEqual(receiver.data(), data)


if __name__ == "__main__":
    unittest.main()
