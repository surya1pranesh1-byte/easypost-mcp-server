import secrets


def generate_secure_token() -> str:
    return secrets.token_hex(32)


def generate_authorization_code() -> str:
    return secrets.token_hex(16)
