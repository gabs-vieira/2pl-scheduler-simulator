from dataclasses import dataclass, field


@dataclass
class Lock:
    mode: str  # "S" or "X"
    owners: set[int] = field(default_factory=set)


class LockTable:
    def __init__(self):
        self.locks: dict[str, Lock] = {}

    def __str__(self):
        if not self.locks:
            return "(empty)"
        return ", ".join(
            f"{item}: {lock.mode} {sorted(f'T{t}' for t in lock.owners)}"
            for item, lock in self.locks.items()
        )

    def blockers(self, tid, kind, item):
        """Who keeps tid from getting the lock. Empty set means it can be granted."""
        lock = self.locks.get(item)
        if lock is None:
            return set()

        others = lock.owners - {tid}
        if kind == "r":
            return others if lock.mode == "X" else set()
        # for a write any other owner blocks, which also covers the S -> X upgrade
        return others

    def grant(self, tid, kind, item):
        """Assumes blockers() is empty. Returns the lock event to print, or None."""
        lock = self.locks.get(item)

        if lock is None:
            mode = "S" if kind == "r" else "X"
            self.locks[item] = Lock(mode, {tid})
            return f"l{mode.lower()}{tid}({item})"

        if tid in lock.owners and (lock.mode == "X" or kind == "r"):
            return None

        if kind == "r":
            lock.owners.add(tid)
            return f"ls{tid}({item})"

        lock.mode = "X"
        return f"lx{tid}({item}) [upgrade]"

    def release_all(self, tid):
        released = []
        for item, lock in list(self.locks.items()):
            if tid in lock.owners:
                lock.owners.discard(tid)
                released.append(f"u{tid}({item})")
                if not lock.owners:
                    del self.locks[item]
        return released
