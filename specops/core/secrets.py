"""Secret key names, redaction helpers, and validation for API.

Re-exports from specops_lib.config.helpers and adds admin-specific helpers.
"""

from specops_lib.config.helpers import redact
from specops_lib.config.schema import Config


def global_config_redacted() -> dict:
    """Return default Config with secrets redacted (for API)."""
    return redact(Config().model_dump(by_alias=False))
