"""Strict 2PL scheduler: turns the initial history into the final history."""

from collections import deque

from scheduler.deadlock import build_wait_for_graph, find_cycle
from scheduler.history import Operation, format_history
from scheduler.locks import LockTable


class Scheduler:
    def __init__(self, operations: list[Operation], database: dict[str, int]):
        self.initial: deque[Operation] = deque(operations)
        self.final: list[Operation] = []
        self.waiting: dict[int, list[Operation]] = {}
        self.database = database
        self.table = LockTable()
        # tid -> [(item, old value)], so an abort can roll back
        self.undo: dict[int, list[tuple[str, int]]] = {}
        self.log: list[str] = []
        self.steps: list[dict] = []

    def run(self):
        while self.initial:
            op = self.initial.popleft()
            self.log.append(f"\n>> {op}")
            start = len(self.log)

            self.process(op)
            self.wake_up()
            self.check_deadlock()

            self.steps.append({
                "op": str(op),
                "events": [line.strip() for line in self.log[start:]],
                "locks": str(self.table),
                "waiting": self.format_waiting() or "-",
                "final": format_history(self.final),
            })

            self.log.append(f"   locks: {self.table}")
            self.log.append(f"   final: {format_history(self.final)}")

        # happens when someone waits for a transaction that never commits
        if self.waiting:
            self.log.append(f"\n!! history ended with transactions still waiting: {self.format_waiting()}")
        if self.table.locks:
            self.log.append(f"\n!! locks still held at the end: {self.table}")

    def format_waiting(self):
        return ", ".join(f"T{tid}: {format_history(ops)}" for tid, ops in self.waiting.items())

    def blockers_of(self, op: Operation) -> set[int]:
        if op.kind == "c":
            return set()
        return self.table.blockers(op.tid, op.kind, op.item)

    def process(self, op: Operation):
        # a waiting transaction stays in order, even if this operation's lock is free
        if op.tid in self.waiting:
            self.waiting[op.tid].append(op)
            self.log.append(f"   {op} waits: T{op.tid} is already waiting")
            return

        blockers = self.blockers_of(op)
        if blockers:
            self.waiting[op.tid] = [op]
            who = ", ".join(f"T{t}" for t in sorted(blockers))
            self.log.append(f"   {op} waits: blocked by {who}")
            return

        self.execute(op)

    def execute(self, op: Operation):
        if op.kind == "c":
            self.undo.pop(op.tid, None)
            # strict 2PL: locks are only released here and on abort
            released = self.table.release_all(op.tid)
            self.log.append(f"   {op} commits, releases: {' '.join(released) or '(no locks)'}")
            self.final.append(op)
            return

        item = op.item
        assert item is not None

        lock_event = self.table.grant(op.tid, op.kind, item)
        if lock_event:
            self.log.append(f"   {lock_event}")

        if op.kind == "r":
            self.log.append(f"   {op} reads {item} = {self.database[item]}")
        else:
            old = self.database[item]
            self.undo.setdefault(op.tid, []).append((item, old))
            self.database[item] = old + 1
            self.log.append(f"   {op} writes {item}: {old} -> {self.database[item]}")

        self.final.append(op)

    def wake_up(self):
        # a commit inside the loop can unblock a transaction we already passed,
        # so keep looping until a full pass moves nobody
        moved = True
        while moved:
            moved = False
            for tid in list(self.waiting):
                queue = self.waiting[tid]
                while queue and not self.blockers_of(queue[0]):
                    op = queue.pop(0)
                    self.log.append(f"   T{tid} stops waiting: {op}")
                    self.execute(op)
                    moved = True
                if not queue:
                    del self.waiting[tid]

    def search_cycle(self) -> list[int] | None:
        graph = build_wait_for_graph(self.waiting, self.table)
        for tid in sorted(self.waiting):
            cycle = find_cycle(graph, tid)
            if cycle:
                return cycle
        return None

    def check_deadlock(self):
        cycle = self.search_cycle()
        while cycle:
            # victim is the youngest transaction (highest number)
            victim = max(cycle)
            path = " -> ".join(f"T{t}" for t in cycle)
            self.log.append(f"   DEADLOCK: {path}, victim T{victim} (youngest)")
            self.abort(victim)
            cycle = self.search_cycle()

    def abort(self, tid: int):
        self.undo_writes(tid)

        executed = [op for op in self.final if op.tid == tid]
        self.final = [op for op in self.final if op.tid != tid]
        released = self.table.release_all(tid)

        # the whole transaction goes to the end, in its original order
        waiting = self.waiting.pop(tid, [])
        pending = [op for op in self.initial if op.tid == tid]
        self.initial = deque(op for op in self.initial if op.tid != tid)
        restart = executed + waiting + pending
        self.initial.extend(restart)

        self.log.append(f"   a{tid}: releases {' '.join(released) or '(no locks)'}")
        self.log.append(f"   T{tid} restarts at the end of the history: {format_history(restart)}")

        self.wake_up()

    def undo_writes(self, tid: int):
        # in reverse, so writing x twice goes back to the value before the first write
        for item, old in reversed(self.undo.pop(tid, [])):
            self.database[item] = old
