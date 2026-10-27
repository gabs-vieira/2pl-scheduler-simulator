import unittest

from scheduler.deadlock import build_wait_for_graph, find_cycle
from scheduler.history import Operation
from scheduler.locks import LockTable


class TestFindCycle(unittest.TestCase):
    def test_two_transaction_cycle(self):
        self.assertEqual(find_cycle({1: {2}, 2: {1}}, 2), [2, 1, 2])

    def test_three_transaction_cycle(self):
        self.assertEqual(find_cycle({1: {2}, 2: {3}, 3: {1}}, 1), [1, 2, 3, 1])

    def test_no_cycle(self):
        self.assertIsNone(find_cycle({1: {2}}, 1))

    def test_cycle_not_through_start(self):
        # T3 waits for T1, but the cycle is only between T1 and T2
        self.assertIsNone(find_cycle({3: {1}, 1: {2}, 2: {1}}, 3))

    def test_backtracks_from_dead_end(self):
        # T1 -> T2 leads nowhere; the cycle goes through T3
        self.assertEqual(find_cycle({1: {2, 3}, 3: {1}}, 1), [1, 3, 1])


class TestWaitForGraph(unittest.TestCase):
    def test_edges_come_from_first_blocked_operation(self):
        table = LockTable()
        table.grant(1, "r", "x")
        table.grant(2, "r", "y")
        waiting = {
            1: [Operation(1, "w", "y"), Operation(1, "c", None)],
            2: [Operation(2, "w", "x")],
        }
        self.assertEqual(build_wait_for_graph(waiting, table), {1: {2}, 2: {1}})


if __name__ == "__main__":
    unittest.main()
