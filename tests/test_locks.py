import unittest

from scheduler.locks import LockTable


class TestLockTable(unittest.TestCase):
    def setUp(self):
        self.table = LockTable()

    def test_shared_locks_are_compatible(self):
        self.table.grant(1, "r", "x")
        self.assertEqual(self.table.blockers(2, "r", "x"), set())

    def test_exclusive_blocks_read(self):
        self.table.grant(1, "w", "x")
        self.assertEqual(self.table.blockers(2, "r", "x"), {1})

    def test_shared_blocks_write(self):
        self.table.grant(1, "r", "x")
        self.table.grant(2, "r", "x")
        self.assertEqual(self.table.blockers(3, "w", "x"), {1, 2})

    def test_upgrade_when_sole_owner(self):
        self.table.grant(1, "r", "x")
        self.assertEqual(self.table.blockers(1, "w", "x"), set())
        self.assertEqual(self.table.grant(1, "w", "x"), "lx1(x) [upgrade]")
        self.assertEqual(self.table.locks["x"].mode, "X")

    def test_no_upgrade_when_shared_with_others(self):
        self.table.grant(1, "r", "x")
        self.table.grant(2, "r", "x")
        self.assertEqual(self.table.blockers(1, "w", "x"), {2})

    def test_already_holds_the_lock(self):
        self.table.grant(1, "w", "x")
        self.assertIsNone(self.table.grant(1, "r", "x"))

    def test_release_all(self):
        self.table.grant(1, "r", "x")
        self.table.grant(1, "w", "y")
        self.table.grant(2, "r", "x")
        self.assertEqual(self.table.release_all(1), ["u1(x)", "u1(y)"])
        self.assertEqual(self.table.blockers(3, "w", "y"), set())
        self.assertEqual(self.table.blockers(3, "w", "x"), {2})


if __name__ == "__main__":
    unittest.main()
