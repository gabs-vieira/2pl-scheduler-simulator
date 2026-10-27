import unittest

from scheduler.database import create_database
from scheduler.history import parse_history
from scheduler.scheduler import Scheduler
from scheduler.step_table import format_table


def run(text):
    operations = parse_history(text)
    scheduler = Scheduler(operations, create_database(operations))
    scheduler.run()
    return scheduler


class TestStepTable(unittest.TestCase):
    def test_one_step_per_history_operation(self):
        s = run("r1(x) w2(y) r2(x) w1(y) c1 c2")
        self.assertEqual([step["op"] for step in s.steps], ["r1(x)", "w2(y)", "r2(x)", "w1(y)", "c1", "c2"])

    def test_step_keeps_waiting_and_final_at_the_end_of_the_step(self):
        s = run("r1(x) w2(y) r2(x) w1(y) c1 c2")
        c1 = s.steps[4]
        self.assertEqual(c1["waiting"], "T1: w1(y) c1")
        self.assertEqual(c1["final"], "r1(x) w2(y) r2(x)")

    def test_table_shows_the_deadlock(self):
        s = run("w1(x) w2(y) r1(y) r2(x) c1 c2")
        self.assertIn("DEADLOCK: T1 -> T2 -> T1", format_table(s.steps))


if __name__ == "__main__":
    unittest.main()
