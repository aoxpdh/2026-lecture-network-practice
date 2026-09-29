"""Save actual iterative query paths, including no-glue sub-walks."""
import json
from pathlib import Path
from task1_resolve import Resolver, VERIFY_NAMES, dig_answer


def main():
    records = []
    for name, kind in VERIFY_NAMES:
        resolver = Resolver()
        record = {"name": name, "kind": kind}
        try:
            address, path = resolver.resolve(name)
            record.update(address=address, path=path, reference=dig_answer(name))
        except RuntimeError as exc:
            record["error"] = str(exc)
        record["events"] = resolver.events
        records.append(record)
        print(name, record.get("address", record.get("error")), len(resolver.path), flush=True)
    out = Path(__file__).parent / "out"
    out.mkdir(exist_ok=True)
    (out / "resolve.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
