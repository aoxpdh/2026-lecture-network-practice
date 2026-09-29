"""Compare backoff factors without modifying the supplied simulator."""
import bench
from task3_congestion import YourControl


def main():
    for factor in (0.5, 0.6, 0.65, 0.7, 0.8):
        class Variant(YourControl):
            def __init__(self):
                super().__init__()
                self.backoff = factor

        bench.show(f"beta={factor}", bench.simulate(Variant))


if __name__ == "__main__":
    main()
