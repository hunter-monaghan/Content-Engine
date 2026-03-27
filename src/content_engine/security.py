from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}", re.IGNORECASE),
    "api_key_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|token|secret)\b\s*[:=]\s*[\"'][^\"'\n]{8,}[\"']"
    ),
    "private_key_block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}

DEFAULT_IGNORES = {
    ".git/",
    ".venv/",
    "venv/",
    "__pycache__/",
    "output/",
    "build/",
    "dist/",
}

TEXT_EXTENSIONS = {
    ".env",
    ".example",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(slots=True)
class SecurityFinding:
    path: str
    rule: str
    line_number: int
    preview: str


def scan_repository(root: Path) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if _is_ignored(relative):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name != ".env.example":
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(_scan_file(relative, content))
    return findings


def _scan_file(relative_path: str, content: str) -> list[SecurityFinding]:
    results: list[SecurityFinding] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if relative_path == ".env.example":
            continue
        for rule, pattern in SECRET_PATTERNS.items():
            if pattern.search(line):
                results.append(
                    SecurityFinding(
                        path=relative_path,
                        rule=rule,
                        line_number=line_number,
                        preview=_sanitize_preview(line),
                    )
                )
    return results


def format_findings(findings: list[SecurityFinding]) -> str:
    if not findings:
        return "No obvious secrets detected."
    lines = ["Potential secrets detected:"]
    for finding in findings:
        lines.append(
            f"- {finding.path}:{finding.line_number} [{finding.rule}] {finding.preview}"
        )
    return "\n".join(lines)


def _is_ignored(relative_path: str) -> bool:
    return any(relative_path.startswith(prefix) for prefix in DEFAULT_IGNORES)


def _sanitize_preview(line: str) -> str:
    stripped = line.strip()
    if len(stripped) <= 16:
        return stripped
    return stripped[:6] + "..." + stripped[-4:]
