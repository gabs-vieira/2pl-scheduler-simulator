import unittest

from scheduler.database import create_database
from scheduler.history import format_history, parse_history
from scheduler.scheduler import Scheduler


def run(text):
    operations = parse_history(text)
    scheduler = Scheduler(operations, create_database(operations))
    scheduler.run()
    return scheduler


class TestScheduler(unittest.TestCase):
    def test_no_conflict_keeps_the_order(self):
        s = run("r1(x) w2(y) c1 c2")
        self.assertEqual(format_history(s.final), "r1(x) w2(y) c1 c2")

    def test_commit_waits_behind_blocked_operation(self):
        s = run("r1(x) w2(y) r2(x) w1(y) c1 c2")
        self.assertEqual(format_history(s.final), "r1(x) w2(y) r2(x) c2 w1(y) c1")
        self.assertEqual(s.waiting, {})

    def test_upgrade_and_cascading_wake_up(self):
        s = run("r1(x) r2(x) w1(x) c1 w2(y) r3(y) c2 c3")
        self.assertEqual(format_history(s.final), "r1(x) r2(x) w2(y) c2 w1(x) c1 r3(y) c3")
        self.assertIn("   lx1(x) [upgrade]", s.log)

    def test_write_updates_the_database(self):
        s = run("w1(x) w1(x) c1 w2(x) c2")
        self.assertEqual(s.database, {"x": 3})
        self.assertEqual(s.undo, {})  # commit clears the undo log

    def test_undo_restores_value_before_first_write(self):
        s = run("w1(x) w1(x) w1(y)")  # no commit: undo log is kept
        self.assertEqual(s.database, {"x": 2, "y": 1})
        s.undo_writes(1)
        self.assertEqual(s.database, {"x": 0, "y": 0})

    def test_deadlock_aborts_youngest_and_reruns_at_the_end(self):
        s = run("r1(x) r2(y) w1(y) w2(x) c1 c2")
        self.assertIn("   DEADLOCK: T1 -> T2 -> T1, victim T2 (youngest)", s.log)
        self.assertEqual(format_history(s.final), "r1(x) w1(y) c1 r2(y) w2(x) c2")
        self.assertEqual(s.waiting, {})
        self.assertEqual(s.table.locks, {})

    def test_three_transaction_deadlock(self):
        s = run("r1(x) r2(y) r3(z) w1(y) w2(z) w3(x) c1 c2 c3")
        self.assertIn("   DEADLOCK: T1 -> T2 -> T3 -> T1, victim T3 (youngest)", s.log)
        self.assertEqual(
            format_history(s.final), "r1(x) r2(y) w2(z) c2 w1(y) c1 r3(z) w3(x) c3"
        )

    def test_abort_undoes_victim_writes(self):
        # w2(y) writes y = 1 before the deadlock; the abort sets y back to 0
        s = run("w1(x) w2(y) w1(y) w2(x) c1 c2")
        self.assertEqual(format_history(s.final), "w1(x) w1(y) c1 w2(y) w2(x) c2")
        self.assertEqual(s.database, {"x": 2, "y": 2})

    def test_wait_without_cycle_is_not_a_deadlock(self):
        # T2 waits for T1, but T1 never commits: it stays waiting, no abort
        s = run("w1(x) r2(x) c2")
        self.assertFalse(any("DEADLOCK" in line for line in s.log))
        self.assertEqual(set(s.waiting), {2})


if __name__ == "__main__":
    unittest.main()
