import uuid
import re


def parse_user_agent(ua: str):
    result = {
        'model': 'SM-S938B',
        'os': 'Android',
        'os_version': '15'
    }
    if not ua:
        return result
    # ---- iOS ----
    ios_match = re.search(r"\((iPhone|iPad).*?OS (\d+[_\.\d+]*)", ua)
    if ios_match:
        result["model"] = ios_match.group(1)
        result["os"] = "iOS"
        result["os_version"] = ios_match.group(2).replace("_", ".")
        return result

    # ---- Android ----
    android_os = re.search(r"Android (\d+[\.\d+]*)", ua)
    android_model = re.search(r"Android [^;]+;\s*([^;\)]+)", ua)

    if android_os:
        result["os"] = "Android"
        result["os_version"] = android_os.group(1)

    if android_model:
        result["model"] = android_model.group(1).strip()

    return result


def is_valid_email(email):
    """
    Basic regex check to ensure string looks like an email.
    """
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

def is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False