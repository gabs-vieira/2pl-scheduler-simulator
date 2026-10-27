"""Operations and parsing of the initial history."""

import re
from dataclasses import dataclass

# r1(x), w2(y) or c1
OPERATION_PATTERN = re.compile(r"^([rw])(\d+)\((\w+)\)$|^c(\d+)$")


@dataclass
class Operation:
    tid: int          # transaction number (T1 -> 1)
    kind: str         # "r" (read), "w" (write) or "c" (commit)
    item: str | None  # data item name; None for commits

    def __str__(self):
        if self.kind == "c":
            return f"c{self.tid}"
        return f"{self.kind}{self.tid}({self.item})"


def parse_history(text):
    """Turns 'r1(x) w2(x) c1' into a list of Operation."""
    operations = []
    for token in text.split():
        m = OPERATION_PATTERN.match(token)
        if not m:
            raise ValueError(f"invalid operation: {token}")
        if m.group(4):
            operations.append(Operation(int(m.group(4)), "c", None))
        else:
            operations.append(Operation(int(m.group(2)), m.group(1), m.group(3)))

    return operations


def format_history(operations):
    """Joins a list of operations back into text: 'r1(x) w2(x) c1'."""
    return " ".join(str(op) for op in operations)
