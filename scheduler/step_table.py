COLUMNS = ["arrives", "what happened", "locks", "waiting", "final"]


def build_rows(steps):
    # one row per event; the state columns only go on the last row of each step
    blocks = []
    for step in steps:
        events = step["events"] or ["(nothing)"]
        block = []
        for i, event in enumerate(events):
            last = i == len(events) - 1
            block.append([
                step["op"] if i == 0 else "",
                event,
                step["locks"] if last else "",
                step["waiting"] if last else "",
                step["final"] if last else "",
            ])
        blocks.append(block)
    return blocks


def format_table(steps):
    blocks = build_rows(steps)

    widths = [len(name) for name in COLUMNS]
    for block in blocks:
        for row in block:
            widths = [max(w, len(cell)) for w, cell in zip(widths, row)]

    def join(cells):
        return " │ ".join(cell.ljust(w) for cell, w in zip(cells, widths)).rstrip()

    separator = "─┼─".join("─" * w for w in widths)

    output = [join(COLUMNS), separator]
    for block in blocks:
        output.extend(join(row) for row in block)
        output.append(separator)
    return "\n".join(output)
