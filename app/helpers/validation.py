import re


def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char.isalpha() for char in password):
        return False
    return True


def validate_email(email: str) -> bool:
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_regex, email) is not None


def validate_username(username: str) -> bool:
    if len(username) < 3 or len(username) > 30:
        return False
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False
    return True