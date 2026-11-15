"""Append-only raw record of every judged pair (judge_records.jsonl), the SMV files (smv/<sha256>.smv) and a run header (run_header.json).
Every aggregate can be recomputed from these files. A rerun with the same record directory skips pair ids already written (resume)."""
import hashlib
import json
import os
import time


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Recorder:
    def __init__(self, directory, header=None):
        self.dir = directory
        os.makedirs(os.path.join(directory, "smv"), exist_ok=True)
        self.path = os.path.join(directory, "judge_records.jsonl")
        self.done = set()
        if os.path.exists(self.path):
            for line in open(self.path, encoding="utf-8"):
                if line.strip():
                    try:
                        self.done.add(json.loads(line)["pair_id"])
                    except Exception:  # noqa: BLE001
                        pass
        hp = os.path.join(directory, "run_header.json")
        if header is not None and not os.path.exists(hp):
            header = dict(header)
            header.setdefault("started_at", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
            json.dump(header, open(hp, "w"), indent=1, ensure_ascii=False)

    def has(self, pair_id):
        return pair_id in self.done

    def write(self, record, smv_texts):
        for sha, text in smv_texts.items():
            p = os.path.join(self.dir, "smv", sha + ".smv")
            if not os.path.exists(p):
                with open(p, "w") as f:
                    f.write(text)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.done.add(record["pair_id"])
