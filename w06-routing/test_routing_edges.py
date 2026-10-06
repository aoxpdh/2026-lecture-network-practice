"""Extra correctness checks; run with python3 -m unittest test_routing_edges."""
import random
import unittest

import task1_linkstate as linkstate
import task3_reconverge as routing


class RoutingEdges(unittest.TestCase):
    def test_disconnected_and_tied_paths(self):
        graph = {"s": {"a": 1, "b": 1}, "a": {"s": 1, "t": 1},
                 "b": {"s": 1, "t": 1}, "t": {"a": 1, "b": 1}, "x": {}}
        self.assertEqual(linkstate.dijkstra(graph, "s"), {"a": 1, "b": 1, "t": 2})
        self.assertEqual(linkstate.forwarding_table(graph, "s"),
                         {"a": "a", "b": "b", "t": "a"})
        self.assertEqual(linkstate.forwarding_table(graph, "x"), {})

    def test_disconnection_restoration_and_equal_cost_alternative(self):
        graph = {"s": {"a": 1}, "a": {"s": 1, "b": 1}, "b": {}, "x": {}}
        graph["b"]["a"] = 1
        router = routing.YourRouter(graph, "s")
        reference = routing.FullRecompute(graph, "s")
        for event in [("a", "b", None), ("b", "x", 1), ("s", "x", 2),
                      ("a", "b", 2), ("s", "x", None), ("s", "a", None),
                      ("s", "a", 1), ("s", "a", 1)]:
            router.link_change(*event)
            reference.link_change(*event)
            self.assertEqual(router.table, reference.table, event)

    def test_random_events_against_reference(self):
        for seed in range(20):
            rng = random.Random(seed)
            nodes = [f"r{i:02d}" for i in range(20)]
            graph = {n: {} for n in nodes}
            router = routing.YourRouter(graph, nodes[0])
            reference = routing.FullRecompute(graph, nodes[0])
            for step in range(300):
                a, b = rng.sample(nodes, 2)
                cost = None if rng.random() < 0.4 else rng.randint(1, 5)
                router.link_change(a, b, cost)
                reference.link_change(a, b, cost)
                self.assertEqual(router.table, reference.table, (seed, step, a, b, cost))
                self.assertEqual(linkstate.forwarding_table(reference.graph, nodes[0]),
                                 reference.table, (seed, step))


if __name__ == "__main__":
    unittest.main()
