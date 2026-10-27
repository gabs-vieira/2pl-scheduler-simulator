import sys
from pathlib import Path

from scheduler.database import create_database
from scheduler.history import format_history, parse_history
from scheduler.scheduler import Scheduler
from scheduler.step_table import format_table

USAGE = """Usage:
    python3 main.py "r1(x) w2(y) r2(x) w1(y) c1 c2"
    python3 main.py examples/no_conflict.txt
    python3 main.py --table examples/no_conflict.txt"""


def read_input(argument):
    # accepts the history itself or a path to a file with it
    path = Path(argument)
    if path.is_file():
        return path.read_text()
    return argument


if __name__ == "__main__":
    args = sys.argv[1:]
    as_table = "--table" in args
    if as_table:
        args.remove("--table")

    if len(args) != 1:
        print(USAGE)
        sys.exit(1)

    try:
        initial_history = parse_history(read_input(args[0]))
    except ValueError as error:
        print("Error in the history:", error)
        sys.exit(1)
    database = create_database(initial_history)

    print("Initial history:", format_history(initial_history))
    print("Initial database:", database)

    scheduler = Scheduler(initial_history, database)
    scheduler.run()
    if as_table:
        print()
        print(format_table(scheduler.steps))
        # still show the end-of-run warnings
        for line in scheduler.log:
            if line.startswith("\n!!"):
                print(line)
    else:
        print("\n".join(scheduler.log))

    print("\nFinal history:", format_history(scheduler.final))
    print("Final database:", database)
