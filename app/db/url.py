from urllib.parse import quote


def normalize_database_url(database_url: str) -> str:
    """Normalize provider URLs and tolerate unescaped passwords copied from dashboards."""
    if database_url.startswith("postgresql+"):
        return _quote_postgres_userinfo(database_url)
    if database_url.startswith("postgresql://"):
        return _quote_postgres_userinfo(database_url.replace("postgresql://", "postgresql+psycopg://", 1))
    if database_url.startswith("postgres://"):
        return _quote_postgres_userinfo(database_url.replace("postgres://", "postgresql+psycopg://", 1))
    return database_url


def _quote_postgres_userinfo(database_url: str) -> str:
    scheme, separator, rest = database_url.partition("://")
    if not separator or "@" not in rest:
        return database_url

    userinfo, host_and_path = rest.rsplit("@", 1)
    if ":" not in userinfo:
        encoded_userinfo = quote(userinfo, safe="%.")
    else:
        username, password = userinfo.split(":", 1)
        encoded_userinfo = f"{quote(username, safe='%.')}:{quote(password, safe='%')}"
    return f"{scheme}://{encoded_userinfo}@{host_and_path}"
