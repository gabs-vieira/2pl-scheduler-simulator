"""Deadlock detection: wait-for graph and cycle search.

Victim choice (lives in the scheduler): the youngest transaction (highest tid).
Another option would be the one with fewer operations in the final history,
to throw away less work.
"""


def build_wait_for_graph(waiting, table) -> dict[int, set[int]]:
    """
    Builds the wait-for graph: tid -> set of tids it is waiting for.

    Ex.: T1 waits for y (held by T2) and T2 waits for x (held by T1)
         -> {1: {2}, 2: {1}}
    """
    graph = {}

    for tid, queue in waiting.items():
        # the transaction is stuck because of the first operation in its queue;
        # the others are just waiting their turn behind it
        op = queue[0]

        # ask the table, NOW, who is blocking this operation
        # (recomputed instead of stored: the blockers may have changed)
        blockers = table.blockers(tid, op.kind, op.item)

        if blockers:
            graph[tid] = blockers

    return graph


def find_cycle(graph, start) -> list[int] | None:
    """
    Looks for a path that leaves `start` and comes BACK to `start`.
    If it finds one, that is a cycle, which means deadlock.

    Returns the cycle, ex.: [2, 1, 2] (T2 waits for T1, which waits for T2).
    Returns None if no cycle goes through `start`.
    """
    path = [start]       # transactions we went through, in order
    visited = {start}    # so we don't loop forever on a cycle that doesn't include `start`

    def search(tid):
        # check every transaction `tid` is waiting for
        for neighbor in sorted(graph.get(tid, set())):

            # back to the start: found the cycle
            if neighbor == start:
                return path + [start]

            # already been here and it led nowhere: skip
            if neighbor in visited:
                continue

            # move forward
            visited.add(neighbor)
            path.append(neighbor)

            cycle = search(neighbor)
            if cycle:
                return cycle

            # dead end: step back and try the next neighbor
            path.pop()

        return None

    return search(start)
