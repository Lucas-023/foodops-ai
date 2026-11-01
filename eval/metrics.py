def tool_selection_accuracy(expected: list[str], called: list[str]) -> float:
    """1.0 when the set of called tools matches the expected set exactly."""
    return float(set(expected) == set(called))


def tool_selection_f1(expected: list[str], called: list[str]) -> float:
    exp, got = set(expected), set(called)
    if not exp and not got:
        return 1.0
    tp = len(exp & got)
    if tp == 0:
        return 0.0
    precision, recall = tp / len(got), tp / len(exp)
    return 2 * precision * recall / (precision + recall)


def recall_at_k(relevant: list[str], retrieved: list[str], k: int) -> float:
    if not relevant:
        return 1.0
    return len(set(relevant) & set(retrieved[:k])) / len(set(relevant))


def answer_contains(answer: str, expected: list[str]) -> float:
    if not expected:
        return 1.0
    lowered = answer.lower()
    return sum(e.lower() in lowered for e in expected) / len(expected)
