import re
from config import EXPECTED_STATUS_CODES, VALID_PROTOCOLS

def ensure_structure(state: dict) -> dict:
    """
    מוודא שכל שדות החובה קיימים במבנה ה־state.
    """
    state.setdefault("target", {})
    state["target"].setdefault("ip", "")
    state["target"].setdefault("os", "")
    state["target"].setdefault("services", [])

    # עבור כל שירות ברשימה, ודא שהפורט, הפרוטוקול והשירות קיימים, אחרת הסר את השירות
    state["target"]["services"] = [
        service for service in state["target"]["services"]
        if service.get("port") and service.get("protocol") and service.get("service")
    ]

    state.setdefault("web_directories_status", {})
    for code in EXPECTED_STATUS_CODES:
        state["web_directories_status"].setdefault(code, {"": ""})

    return state

def validate_services_format(services: list) -> list:
    """
    מוודא שכל שירות במבנה תקני: פורט מספרי, פרוטוקול tcp/udp, ושם שירות באנגלית.
    """
    valid = []
    for s in services:
        try:
            port = int(s.get("port", ""))
            protocol = s.get("protocol", "").lower()
            service = s.get("service", "").lower()
            if (
                0 < port <= 65535 and
                protocol in VALID_PROTOCOLS and
                re.match(r'^[a-z0-9\-_\.]+$', service)
            ):
                valid.append({
                    "port": str(port),
                    "protocol": protocol,
                    "service": service
                })
        except:
            continue
    return valid

def filter_invalid_services(services: list) -> list:
    """
    מסנן שירותים פיקטיביים לפי פורטים או שמות בעייתיים.
    """
    suspicious_ports = {0, 1, 9999}
    blocked_names = {"none", "fake"}

    return [
        s for s in services
        if int(s["port"]) not in suspicious_ports
        and s["service"] not in blocked_names
    ]

def clean_web_directories(web_dirs: dict) -> dict:
    """
    מנקה ומוודאת את מבנה web_directories_status:
    - שומר רק נתיבים חוקיים שמתחילים ב-"/".
    - מוסיף '"" : ""' רק אם היה לפחות נתיב עם '/'.
    - תמיד מחזיר את כל חמשת הקטגוריות: 200, 401, 403, 404, 503.
    """
    cleaned = {}

    for code in EXPECTED_STATUS_CODES:
        entries = web_dirs.get(code, {})
        valid_paths = {}

        has_slash_path = False

        if isinstance(entries, dict):
            for path, label in entries.items():
                if isinstance(path, str) and isinstance(label, str):
                    if path.startswith("/") and path.strip():
                        valid_paths[path] = label
                        has_slash_path = True  # היה לפחות נתיב אמיתי

        # אם לא היו נתיבים חוקיים בכלל — נשאיר "": ""
        # אם כן היו נתיבים עם "/", נכניס "": "" גם
        if not has_slash_path:
            valid_paths[""] = ""

        cleaned[code] = valid_paths

    return cleaned

def truncate_lists(state: dict, max_services=100, max_paths_per_status=100) -> dict:
    """
    מגביל את האורך של services ונתיבי web.
    """
    state["target"]["services"] = state["target"]["services"][:max_services]
    for code in EXPECTED_STATUS_CODES:
        entries = state["web_directories_status"].get(code, {})
        limited = dict(list(entries.items())[:max_paths_per_status])
        state["web_directories_status"][code] = limited
    return state

def validate_state(state: dict) -> dict:
    """
    פונקציה ראשית שמיישמת את כל שלבי הבדיקה והניקוי.
    """
    state = ensure_structure(state)
    services = state["target"]["services"]
    services = validate_services_format(services)
    services = filter_invalid_services(services)
    state["target"]["services"] = services

    state["web_directories_status"] = clean_web_directories(state["web_directories_status"])
    state = truncate_lists(state)
    return state