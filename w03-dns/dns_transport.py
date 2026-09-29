"""Bounded dig transport and section parsing; no delegation logic here."""
import re
import subprocess


def normalize(name):
    name = name.rstrip(".").lower()
    if not name or len(name) > 253 or any(
        not re.fullmatch(r"[a-z0-9_-]{1,63}", label) for label in name.split(".")
    ):
        raise ValueError("invalid DNS name")
    return name


def query(name, server=None, recursive=True, rtype="A"):
    args = ["dig", "+time=2", "+tries=1", "+recurse" if recursive else "+norecurse"]
    if server:
        args.append("@" + server)
    args.extend([normalize(name) + ".", rtype])
    result = subprocess.run(args, capture_output=True, text=True, timeout=6)
    if result.returncode:
        raise RuntimeError("dig failed: " + (result.stderr or result.stdout).strip()[-300:])
    return parse_response(result.stdout)


def parse_response(text):
    status = re.search(r"status: (\w+)", text)
    flags = re.search(r";; flags: ([^;]*);", text)
    if not status:
        raise RuntimeError("DNS response header missing")
    result = {"status": status.group(1), "aa": bool(flags and "aa" in flags.group(1).split()),
              "answer": [], "authority": [], "additional": []}
    section = None
    for line in text.splitlines():
        match = re.match(r";; (ANSWER|AUTHORITY|ADDITIONAL) SECTION:", line)
        if match:
            section = match.group(1).lower()
        elif line.startswith(";"):
            continue
        elif section and line.strip():
            fields = line.split()
            if len(fields) >= 5 and fields[1].isdigit() and fields[2] == "IN":
                result[section].append({"name": fields[0].rstrip(".").lower(),
                                        "ttl": int(fields[1]), "type": fields[3],
                                        "value": fields[4].rstrip(".").lower()})
    return result
