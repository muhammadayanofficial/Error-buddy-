"""Markdown report export."""


def _fence(code, lang=""):
    ticks = "````" if "```" in code else "```"
    return f"{ticks}{lang}\n{code}\n{ticks}"


def build_markdown(review):
    r, lang = review["result"], review["language"].lower()
    out = [f"# PatchLens AI review #{review['id']}", "", f"- Language: {review['language']}", f"- Created: {review['created_at']}",
           "", "## Summary", "", r.get("summary") or "No summary.", "", "## Submitted code", "", _fence(review["code"], lang)]
    if review.get("error_text"):
        out += ["", "## Error message", "", _fence(review["error_text"])]
    out += ["", "## Findings", ""]
    for n, f in enumerate(r["findings"], 1):
        out += [f"### {n}. [{f['severity'].upper()}] {f['title']}", ""]
        if f["reference"]:
            out += [f"Reference: `{f['reference']}`", ""]
        out += [f"Why it matters: {f['why']}", "", f"Recommended fix: {f['fix']}", ""]
    if not r["findings"]:
        out += ["No findings reported.", ""]
    if r.get("debug"):
        d = r["debug"]
        out += ["## Debugging", "", f"Root cause: {d['root_cause']}", "", d["explanation"], "", f"Correction: {d['correction']}", "", "Verification steps:", ""]
        out += [f"{i}. {s}" for i, s in enumerate(d["verification"], 1)] + [""]
    if r.get("improved"):
        out += ["## Suggested improved version", "", _fence(r["improved"]["code"], lang), "", "Key changes:", ""]
        out += [f"- {c}" for c in r["improved"]["changes"]] + [""]
    if r.get("tests"):
        t = r["tests"]
        out += ["## Recommended tests", "", f"Framework: {t['framework'] or 'unspecified'}. These tests were generated and have not been executed.", "",
                _fence(t["code"], lang), ""]
        out += [f"- {e['name']}: {e['checks']}" for e in t["explanations"]] + [""]
    return "\n".join(out)
