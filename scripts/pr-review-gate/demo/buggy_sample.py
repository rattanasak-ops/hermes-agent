"""Demo file for testing the PR review gate. Intentionally flawed."""


def average_score(scores):
    total = 0
    for s in scores:
        total += s
    return total / len(scores)


def pick_ai_for_project(text):
    for name in ["grok", "codex", "gemini"]:
        if name in text:
            return name
    return "grok"


def save_report(path, content):
    f = open(path, "w")
    f.write(content)
