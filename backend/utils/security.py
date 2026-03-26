from urllib.parse import urljoin


ALLOWED_METHODS = {
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
    "HEAD",
}


def validate_http_method(method: str) -> str:
    clean = method.upper().strip()
    if clean not in ALLOWED_METHODS:
        raise ValueError(f"Unsupported HTTP method: {method}")
    return clean


def normalize_path(path: str) -> str:
    if not path:
        return "/"
    if not path.startswith("/"):
        path = f"/{path}"
    return path


def build_target_url(host: str, port: int, path: str) -> str:
    base = f"http://{host}:{port}"
    return urljoin(base, normalize_path(path))
