import re


SENSITIVE_PATHS = (
    (re.compile(r"(/convites/)[^/?\s]+"), r"\1[token-oculto]"),
    (re.compile(r"(/identidade/verificar-email/)[^/?\s]+"), r"\1[token-oculto]"),
)


def redact_sensitive_text(value):
    for pattern, replacement in SENSITIVE_PATHS:
        value = pattern.sub(replacement, value)
    return value


class RedactSensitivePathsFilter:
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    key: redact_sensitive_text(value) if isinstance(value, str) else value
                    for key, value in record.args.items()
                }
            else:
                record.args = tuple(
                    redact_sensitive_text(value) if isinstance(value, str) else value
                    for value in record.args
                )
        return True
