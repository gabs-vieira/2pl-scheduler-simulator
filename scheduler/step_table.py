"""Step-by-step output as a table (--table option of main.py).

It only formats what the Scheduler already stored in `steps`; the scheduling
logic does not depend on this file. Each step becomes one or more rows:

    arrives   what happened                  locks                   waiting     final
    w1(y)     w1(y) waits: blocked by T2     x: S ['T1', 'T2'], ...  T1: w1(y)   r1(x) w2(y) r2(x)
"""

COLUMNS = ["arrives", "what happened", "locks", "waiting", "final"]


def build_rows(steps):
    """One row per event; locks, waiting and final only on the step's last row (how it ended)."""
    blocks = []
    for step in steps:
        events = step["events"] or ["(nothing)"]
        block = []
        for i, event in enumerate(events):
            first = i == 0
            last = i == len(events) - 1
            block.append([
                step["op"] if first else "",
                event,
                step["locks"] if last else "",
                step["waiting"] if last else "",
                step["final"] if last else "",
            ])
        blocks.append(block)
    return blocks


def format_table(steps):
    """Text for the whole table, with aligned columns and a line between steps."""
    blocks = build_rows(steps)

    widths = [len(name) for name in COLUMNS]
    for block in blocks:
        for row in block:
            widths = [max(current, len(cell)) for current, cell in zip(widths, row)]

    def join(cells):
        return " │ ".join(cell.ljust(width) for cell, width in zip(cells, widths)).rstrip()

    separator = "─┼─".join("─" * width for width in widths)

    output = [join(COLUMNS), separator]
    for block in blocks:
        output.extend(join(row) for row in block)
        output.append(separator)
    return "\n".join(output)
