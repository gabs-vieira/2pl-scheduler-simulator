import unittest

from scheduler.database import create_database
from scheduler.history import Operation, format_history, parse_history


class TestHistory(unittest.TestCase):
    def test_parses_reads_writes_and_commits(self):
        self.assertEqual(
            parse_history("r1(x) w2(y) c1"),
            [Operation(1, "r", "x"), Operation(2, "w", "y"), Operation(1, "c", None)],
        )

    def test_round_trip(self):
        text = "r1(x) w2(y) r2(x) w1(y) c1 c2"
        self.assertEqual(format_history(parse_history(text)), text)

    def test_invalid_operation(self):
        with self.assertRaisesRegex(ValueError, "invalid operation: r1x"):
            parse_history("r1x")

    def test_database_starts_at_zero(self):
        self.assertEqual(create_database(parse_history("r1(x) w2(y) c1")), {"x": 0, "y": 0})


if __name__ == "__main__":
    unittest.main()
