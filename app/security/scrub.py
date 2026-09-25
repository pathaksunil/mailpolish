from pydantic import SecretStr


def reveal_secret(secret: SecretStr) -> str:
    return secret.get_secret_value()
