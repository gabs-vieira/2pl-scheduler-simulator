# 2PL Scheduler Simulator

A simulator of a transaction scheduler that uses **Strict Two-Phase Locking (Strict 2PL)**, the protocol many databases use to keep concurrent transactions from stepping on each other.

You give it an initial history (the order operations *arrive*) and it builds the final history (the order they *actually run*), step by step, showing every lock, wait, deadlock and abort along the way.

Originally built for the Databases course at UCS (Universidade de Caxias do Sul), then rewritten in English.

## Example

```
$ python3 main.py "r1(x) w2(y) r2(x) w1(y) c1 c2"

Initial history: r1(x) w2(y) r2(x) w1(y) c1 c2
Final history:   r1(x) w2(y) r2(x) c2 w1(y) c1
```

`w1(y)` has to wait because T2 holds an exclusive lock on `y`, and `c1` waits behind it. When `c2` arrives, T2 releases its locks and T1 finishes.

## How it works

**Locks**

- a read (`r`) needs a shared lock (S); a write (`w`) needs an exclusive lock (X);
- S is compatible with S; any other combination between different transactions blocks;
- a transaction never blocks itself: if it is the only S owner and wants to write, S is upgraded to X;
- locks are only released on commit or abort. That's the *Strict* part: nobody reads or overwrites a value that may still be rolled back.

**Waiting**

If a lock can't be granted, the whole transaction waits. Its next operations queue up behind the blocked one, even if their own locks are free.

**Each operation of the history goes through three steps**

1. run it, or put it in the wait queue;
2. try to move whoever was waiting;
3. check for deadlock.

**Deadlocks**

- **Detection:** after each operation, build a wait-for graph (`Ti -> Tj` means Ti is waiting for a lock Tj holds) and look for a cycle with DFS.
- **Victim:** the youngest transaction in the cycle (highest number).
- **Recovery:** undo its writes, remove its operations from the final history, release its locks and put all its operations back at the end of the history.

```
$ python3 main.py examples/simple_deadlock.txt

>> w2(x)
   w2(x) waits: blocked by T1
   DEADLOCK: T1 -> T2 -> T1, victim T2 (youngest)
   a2: releases u2(y)
   T2 restarts at the end of the history: r2(y) w2(x) c2
   T1 stops waiting: w1(y)
   ...

Final history: r1(x) w1(y) c1 r2(y) w2(x) c2
```

## Running

Python 3.10+, no dependencies.

```
python3 main.py "r1(x) w2(y) r2(x) w1(y) c1 c2"
python3 main.py examples/three_way_deadlock.txt
python3 main.py --table examples/no_conflict.txt   # steps as a table
python3 -m unittest                                # tests
```

Input format: operations separated by spaces. `r1(x)` = T1 reads x, `w2(y)` = T2 writes y, `c1` = T1 commits.

Output notation: `ls1(x)` shared lock, `lx1(x)` exclusive lock, `[upgrade]` S became X, `u1(x)` unlock, `a2` T2 aborted.

The database is simulated in memory: every item starts at 0 and each write adds 1, so you can see whether a write happened or was undone.

## Project structure

```
main.py                    CLI: reads the history, runs the scheduler, prints the output
scheduler/history.py       Operation(tid, kind, item) and history parsing
scheduler/database.py      simulated database {item: value}
scheduler/locks.py         LockTable and Lock(mode, owners): grant, block, release
scheduler/scheduler.py     main loop: wait queues, undo log, abort
scheduler/deadlock.py      wait-for graph and cycle search
scheduler/step_table.py    --table output
examples/                  one history per file
tests/                     unittest
```

## Limitations

- no user-requested abort, only aborts caused by deadlock;
- no starvation handling: since the victim is always the youngest, the same transaction can be aborted more than once;
- no fair queue per item: a waiting writer can be overtaken by readers that arrived later (in `r1(x) w2(x) r3(x) c1 c2 c3`, `r3(x)` runs before `w2(x)`).

## License

MIT
