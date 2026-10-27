"""Lock table: shared (S) and exclusive (X) locks per data item."""

from dataclasses import dataclass, field


@dataclass
class Lock:
    mode: str                                  # "S" or "X"
    owners: set[int] = field(default_factory=set)


class LockTable:
    def __init__(self):
        self.locks: dict[str, Lock] = {}       # item -> Lock

    def __str__(self):
        if not self.locks:
            return "(empty)"
        return ", ".join(
            f"{item}: {lock.mode} {sorted(f'T{t}' for t in lock.owners)}"
            for item, lock in self.locks.items()
        )

    def blockers(self, tid, kind, item):
        """Transactions that keep tid from getting the lock. Empty set = can grant."""
        lock = self.locks.get(item)
        if lock is None:
            return set()

        # a transaction never blocks itself
        others = lock.owners - {tid}

        if kind == "r":
            # S is compatible with S; only an X held by someone else blocks
            return others if lock.mode == "X" else set()

        # a write needs X: any other owner blocks (this already covers the upgrade)
        return others

    def grant(self, tid, kind, item):
        """Grants the lock. Only call it when blockers() is empty. Returns what happened, for display."""
        lock = self.locks.get(item)

        if lock is None:
            mode = "S" if kind == "r" else "X"
            self.locks[item] = Lock(mode, {tid})
            return f"l{mode.lower()}{tid}({item})"

        if tid in lock.owners and (lock.mode == "X" or kind == "r"):
            return None  # already holds a strong enough lock

        if kind == "r":
            lock.owners.add(tid)
            return f"ls{tid}({item})"

        # tid is the only S owner and wants to write
        lock.mode = "X"
        return f"lx{tid}({item}) [upgrade]"

    def release_all(self, tid):
        """Releases every lock held by tid (Strict 2PL: only called on commit/abort)."""
        released = []
        for item, lock in list(self.locks.items()):
            if tid in lock.owners:
                lock.owners.discard(tid)
                released.append(f"u{tid}({item})")
                if not lock.owners:
                    del self.locks[item]
        return released
