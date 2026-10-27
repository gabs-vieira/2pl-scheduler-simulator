"""Strict 2PL scheduler: turns the initial history into the final history."""

from collections import deque

from scheduler.deadlock import build_wait_for_graph, find_cycle
from scheduler.history import Operation, format_history
from scheduler.locks import LockTable


class Scheduler:
    def __init__(self, operations: list[Operation], database: dict[str, int]):
        self.initial: deque[Operation] = deque(operations)  # initial history: not evaluated yet
        self.final: list[Operation] = []                     # final history: r/w/c in the order they ran
        self.waiting: dict[int, list[Operation]] = {}        # tid -> operations waiting for a lock
        self.database = database                             # item -> value
        self.table = LockTable()
        self.undo: dict[int, list[tuple[str, int]]] = {}    # tid -> (item, old value), in write order
        self.log: list[str] = []                             # step-by-step output (locks, waits, values)

    def run(self):
        """Main loop: every operation of the initial history goes through the same steps."""
        while self.initial:
            op = self.initial.popleft()
            self.log.append(f"\n>> {op}")

            self.process(op)          # 1. run the incoming operation (or make it wait)
            self.wake_up()            # 2. move whoever was waiting, if possible
            self.check_deadlock()     # 3. if stuck in a cycle, abort the victim

            self.log.append(f"   locks: {self.table}")
            self.log.append(f"   final: {format_history(self.final)}")

        # someone is still waiting when it waits for a transaction that never commits
        if self.waiting:
            stuck = ", ".join(
                f"T{tid}: {format_history(ops)}" for tid, ops in self.waiting.items()
            )
            self.log.append(f"\n!! history ended with transactions still waiting: {stuck}")

        # a transaction without commit (or stuck waiting) ends holding its locks
        if self.table.locks:
            self.log.append(f"\n!! locks still held at the end: {self.table}")

    def blockers_of(self, op: Operation) -> set[int]:
        """Transactions that keep op from running now. Empty = can run."""
        # commit asks for no lock, so it is never blocked
        if op.kind == "c":
            return set()
        return self.table.blockers(op.tid, op.kind, op.item)

    def process(self, op: Operation):
        """Operation that just arrived from the initial history: run it or make it wait."""
        # the transaction is already waiting: the operation goes to the back of its queue,
        # even if its lock is free (a transaction runs in order)
        if op.tid in self.waiting:
            self.waiting[op.tid].append(op)
            self.log.append(f"   {op} waits: T{op.tid} is already waiting")
            return

        # someone holds a conflicting lock: the transaction starts waiting
        blockers = self.blockers_of(op)
        if blockers:
            self.waiting[op.tid] = [op]
            who = ", ".join(f"T{t}" for t in sorted(blockers))
            self.log.append(f"   {op} waits: blocked by {who}")
            return

        self.execute(op)

    def execute(self, op: Operation):
        """Actually runs r, w or c. Only call it when blockers_of(op) is empty."""
        if op.kind == "c":
            # after the commit the writes can no longer be undone
            self.undo.pop(op.tid, None)

            # Strict 2PL: commit (or abort) is the only moment locks are released
            released = self.table.release_all(op.tid)
            self.log.append(f"   {op} commits, releases: {' '.join(released) or '(no locks)'}")
            self.final.append(op)
            return

        item = op.item
        assert item is not None  # r/w always have an item; only commits come with None

        # grant the lock (None = already held a strong enough lock, nothing changes)
        lock_event = self.table.grant(op.tid, op.kind, item)
        if lock_event:
            self.log.append(f"   {lock_event}")

        if op.kind == "r":
            self.log.append(f"   {op} reads {item} = {self.database[item]}")
        else:
            # keep the old value before writing, so an abort can undo it
            old = self.database[item]
            self.undo.setdefault(op.tid, []).append((item, old))
            self.database[item] = old + 1
            self.log.append(f"   {op} writes {item}: {old} -> {self.database[item]}")

        self.final.append(op)

    def wake_up(self):
        """Runs whatever it can from the waiting queues, until nobody can move."""
        # a commit in the middle can release locks and unblock a transaction
        # already checked in this pass, so keep going while someone moved
        moved = True
        while moved:
            moved = False

            # list(...) because a transaction whose queue empties is removed from the dict
            for tid in list(self.waiting):
                queue = self.waiting[tid]

                # run from the front of the queue while it is not blocked
                while queue and not self.blockers_of(queue[0]):
                    op = queue.pop(0)
                    self.log.append(f"   T{tid} stops waiting: {op}")
                    self.execute(op)
                    moved = True

                # empty queue: the transaction is no longer waiting
                if not queue:
                    del self.waiting[tid]

    def search_cycle(self) -> list[int] | None:
        """Is there any cycle in the wait-for graph? Returns the cycle or None."""
        graph = build_wait_for_graph(self.waiting, self.table)

        # every cycle goes through someone who is waiting; try each one
        for tid in sorted(self.waiting):
            cycle = find_cycle(graph, tid)
            if cycle:
                return cycle

        return None

    def check_deadlock(self):
        """While there is a cycle, abort the victim (there can be more than one cycle)."""
        cycle = self.search_cycle()
        while cycle:
            # victim: the youngest transaction (highest number) in the cycle
            victim = max(cycle)
            path = " -> ".join(f"T{t}" for t in cycle)
            self.log.append(f"   DEADLOCK: {path}, victim T{victim} (youngest)")

            self.abort(victim)
            cycle = self.search_cycle()

    def abort(self, tid: int):
        """Aborts tid: undo, remove from the final history, release locks, send operations to the end."""
        # 1. undo its writes in the database
        self.undo_writes(tid)

        # 2. remove from the final history whatever it had already run
        executed = [op for op in self.final if op.tid == tid]
        self.final = [op for op in self.final if op.tid != tid]

        # 3. release its locks (abort releases too, just like commit)
        released = self.table.release_all(tid)

        # 4. gather ALL of its operations, in the original order:
        #    the ones that ran, the ones waiting and the ones that hadn't arrived yet
        waiting = self.waiting.pop(tid, [])
        pending = [op for op in self.initial if op.tid == tid]
        self.initial = deque(op for op in self.initial if op.tid != tid)
        restart = executed + waiting + pending
        self.initial.extend(restart)

        self.log.append(f"   a{tid}: releases {' '.join(released) or '(no locks)'}")
        self.log.append(f"   T{tid} restarts at the end of the history: {format_history(restart)}")

        # 5. the released locks may unblock someone who was waiting
        self.wake_up()

    def undo_writes(self, tid: int):
        """Undoes tid's writes in the database (used when aborting on deadlock)."""
        # backwards: if tid wrote x twice, the right value is the one before the 1st write
        for item, old in reversed(self.undo.pop(tid, [])):
            self.database[item] = old
