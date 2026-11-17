"""Extension hooks of the core (docs/V20_BATCH_DESIGN.md section 8). The core knows only the names; the content of an extension lives in its own folder.
parse(names, dict_all)  -> tuple of enabled extension names (validated); `dict_all` is the old flag --dict-all, an alias of the extension name `dictionary`
split(text)             -> list of names from a shell string such as "dictionary" or "dictionary,other" or "" (all off)"""
KNOWN = ("dictionary",)
DICTIONARY = "dictionary"


def split(text):
    return [x for x in (text or "").replace(",", " ").split() if x]


def parse(names=None, dict_all=False):
    out = []
    for n in list(names or []) + ([DICTIONARY] if dict_all else []):
        for x in split(n):
            if x not in KNOWN:
                raise SystemExit(f"unknown extension {x!r}; known: {', '.join(KNOWN)}")
            if x not in out:
                out.append(x)
    return tuple(out)
