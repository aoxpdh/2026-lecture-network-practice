"""Count mandatory refreshes by name, independently of the cache implementation."""
from collections import Counter
from bench import FIXTURE, workload


def floor():
    expires, counts = {}, Counter()
    for now, name in workload():
        if name not in expires or now >= expires[name]:
            counts[name] += 1
            expires[name] = now + FIXTURE[name][1]
    return counts


if __name__ == "__main__":
    counts = floor()
    for name, count in counts.items():
        print(f"{name}: {count}")
    print("minimum upstream queries:", sum(counts.values()))
