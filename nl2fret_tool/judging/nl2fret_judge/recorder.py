"""Append-only raw record of every judged pair (judge_records.jsonl), the SMV files (smv/<sha256>.smv) and a run header (run_header.json).
Every aggregate can be recomputed from these files. A rerun with the same record directory skips pair ids already written (resume).

Resume after a forced stop (v1.1.0): if the process died while a record was being written, judge_records.jsonl ends with a partial line (no newline,
not a complete JSON object). At start-up the Recorder removes that partial line, keeps its bytes in judge_records.discarded_tail.txt, and the pair is
judged again. Without this, the next record would be appended to the partial text and both would be lost to every reader."""
import hashlib
import json
import os
import sys
import time

TAIL_FILE = "judge_records.discarded_tail.txt"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def split_tail(path):
    """-> (offset, tail, complete). offset: byte position after the last newline of the file (0 when there is none). tail: the bytes after it, b'' when
    they are empty or only whitespace. complete: True when tail is a whole JSON object whose newline is missing (then it is a record, not a partial line)."""
    size = os.path.getsize(path)
    offset = 0
    with open(path, "rb") as f:
        pos = size
        while pos > 0:
            start = max(0, pos - (1 << 16))
            f.seek(start)
            chunk = f.read(pos - start)
            i = chunk.rfind(b"\n")
            if i >= 0:
                offset = start + i + 1
                break
            pos = start
        f.seek(offset)
        tail = f.read()
    if not tail.strip():
        return offset, b"", False
    try:
        complete = isinstance(json.loads(tail.decode("utf-8")), dict)
    except Exception:  # noqa: BLE001  (invalid JSON, or a multi-byte character cut in the middle)
        complete = False
    return offset, tail, complete


class Recorder:
    def __init__(self, directory, header=None):
        self.dir = directory
        os.makedirs(os.path.join(directory, "smv"), exist_ok=True)
        self.path = os.path.join(directory, "judge_records.jsonl")
        self.done = set()
        if os.path.exists(self.path):
            self._repair_tail()
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

    def _repair_tail(self):
        offset, tail, complete = split_tail(self.path)
        if not tail:
            return
        if complete:                       # a whole record, only its newline is missing: keep it and end the line
            with open(self.path, "ab") as f:
                f.write(b"\n")
            return
        with open(os.path.join(self.dir, TAIL_FILE), "ab") as f:
            f.write(f"# {time.strftime('%Y-%m-%dT%H:%M:%S%z')} offset {offset} length {len(tail)}: partial last line of judge_records.jsonl, removed at resume\n".encode())
            f.write(tail + b"\n")
        with open(self.path, "r+b") as f:
            f.truncate(offset)
        print(f"recorder: removed an incomplete last line of judge_records.jsonl ({len(tail)} bytes, interrupted write); the bytes are kept in {TAIL_FILE}; "
              "that pair is judged again", file=sys.stderr, flush=True)

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
