"""
SlothOps Engine — Error Classifier
Heuristic classifier that categorises errors as:
  code | infra | dependency | unknown

Only "code" errors proceed to fix generation.
"""

from __future__ import annotations

from app.models import Classification

# ── Signal lists ─────────────────────────────────────────────────────────

INFRA_SIGNALS: list[str] = [
    "ECONNREFUSED",
    "ETIMEDOUT",
    "ECONNRESET",
    "502",
    "503",
    "504",
    "OOMKilled",
    "heap out of memory",
    "SIGKILL",
    "SIGTERM",
    "connection refused",
    "connection dropped",
    "timeout exceeded",
    "certificate",
    "DNS",
    "pod crash",
    "container exit",
    "ErrImagePull",
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "deadlock",
    "lock wait timeout",
    "too many connections",
    "ThrottlingException",
    "ServiceUnavailableException",
    "RequestLimitExceeded",
    "TooManyRequestsException",
]

INFRA_CONTEXTUAL: list[str] = [
    "database",
    "redis",
    "postgres",
    "mysql",
    "mongodb",
    "elasticsearch",
    "rabbitmq",
    "kafka",
    "memcached",
]

CODE_ERROR_TYPES: list[str] = [
    "TypeError",
    "ReferenceError",
    "RangeError",
    "SyntaxError",
    "URIError",
    "AttributeError",
    "KeyError",
    "IndexError",
    "ValueError",
    "ImportError",
    "NameError",
    "ZeroDivisionError",
    "FileNotFoundError",
    "ModuleNotFoundError",
    "RecursionError",
    "StopIteration",
    "NullPointerException",
    "ClassCastException",
    "ArrayIndexOutOfBoundsException",
    "IllegalArgumentException",
    "StackOverflowError",
    "NumberFormatException",
    "ConcurrentModificationException",
    "UnsupportedOperationException",
    "NoMethodError",
    "ArgumentError",
    "RuntimeError",
    "LoadError",
]

CODE_MESSAGE_SIGNALS: list[str] = [
    "runtime error",
    "index out of range",
    "nil pointer dereference",
    "slice bounds out of range",
    "invalid memory address",
    "panic",
    "unwrap()",
    "thread 'main' panicked",
]

DEPENDENCY_PATHS = [
    "node_modules",
    "site-packages",
    ".venv/",
    "vendor/",
    ".m2/repository",
    ".gradle/caches",
    "target/debug/deps",
    "Pods/",
]


def classify(
    error_type: str | None = None,
    error_message: str | None = None,
    stack_trace: str | None = None,
    file_path: str | None = None,
) -> str:
    """
    Return one of: ``code``, ``infra``, ``dependency``, ``unknown``.

    The combined text of *error_type*, *error_message*, and *stack_trace*
    is checked against signal lists.  *file_path* is checked for
    ``node_modules`` to detect dependency errors.
    """
    combined = " ".join(
        part for part in (error_type, error_message, stack_trace) if part
    ).lower()

    # 1) Dependency check (multi-language)
    if file_path and any(dep_path in file_path for dep_path in DEPENDENCY_PATHS):
        return Classification.DEPENDENCY.value

    # 2) Infra signals (direct match)
    for signal in INFRA_SIGNALS:
        if signal.lower() in combined:
            return Classification.INFRA.value

    # 3) Infra contextual signals (need a pairing keyword)
    connection_keywords = ["connection", "timeout", "refused", "reset"]
    for signal in INFRA_CONTEXTUAL:
        if signal.lower() in combined:
            if any(kw in combined for kw in connection_keywords):
                return Classification.INFRA.value

    # 4) Code signals (error_type matches known error types)
    if error_type and error_type in CODE_ERROR_TYPES:
        return Classification.CODE.value

    # 5) Code signals in error_message (for Go panics, Rust panics)
    error_message_lower = (error_message or "").lower()
    if any(signal in error_message_lower for signal in CODE_MESSAGE_SIGNALS):
        return Classification.CODE.value

    # 6) Default
    return Classification.UNKNOWN.value
