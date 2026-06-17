import uuid


def create_correlation_id(prefix: str = "mcp") -> str:
    return f"{prefix}_{uuid.uuid4()}"
