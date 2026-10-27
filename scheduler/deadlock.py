"""Wait-for graph and cycle search."""


def build_wait_for_graph(waiting, table) -> dict[int, set[int]]:
    """tid -> set of tids it is waiting for, e.g. {1: {2}, 2: {1}}."""
    graph = {}

    for tid, queue in waiting.items():
        # only the first operation is blocked, the rest of the queue is just behind it
        op = queue[0]

        # recomputed every time instead of stored, since blockers change after commits
        blockers = table.blockers(tid, op.kind, op.item)
        if blockers:
            graph[tid] = blockers

    return graph


def find_cycle(graph, start) -> list[int] | None:
    """DFS for a path from start back to start, e.g. [2, 1, 2]. None if there isn't one."""
    path = [start]
    visited = {start}

    def search(tid):
        for neighbor in sorted(graph.get(tid, set())):
            if neighbor == start:
                return path + [start]
            if neighbor in visited:
                continue

            visited.add(neighbor)
            path.append(neighbor)
            cycle = search(neighbor)
            if cycle:
                return cycle
            path.pop()

        return None

    return search(start)
