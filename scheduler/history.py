import re
from dataclasses import dataclass

OPERATION_PATTERN = re.compile(r"^([rw])(\d+)\((\w+)\)$|^c(\d+)$")


@dataclass
class Operation:
    tid: int
    kind: str  # "r", "w" or "c"
    item: str | None  # None for commits

    def __str__(self):
        if self.kind == "c":
            return f"c{self.tid}"
        return f"{self.kind}{self.tid}({self.item})"


def parse_history(text):
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
    return " ".join(str(op) for op in operations)
