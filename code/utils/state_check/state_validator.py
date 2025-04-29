import re
from config import DEFAULT_STATE_STRUCTURE
import copy

def recursive_setdefault(base: dict, default: dict):
    """
    משלים רקורסיבית ערכים חסרים במילון base לפי מבנה default.
    """
    for key, default_value in default.items():
        if key not in base:
            base[key] = copy.deepcopy(default_value)
        elif isinstance(default_value, dict) and isinstance(base[key], dict):
            recursive_setdefault(base[key], default_value)

def clean_list_entries_by_template(actual_list, template_list):
    """
    מנקה איברים לא חוקיים מתוך actual_list על פי המבנה הצפוי ב-template_list.
    כרגע תומך רק בניקוי services לפי port/protocol/service.
    """
    if not template_list or not isinstance(template_list[0], dict):
        return actual_list  # אין תבנית להשוואה
    expected_keys = set(template_list[0].keys())
    return [
        item for item in actual_list
        if isinstance(item, dict) and
           all(k in item and item[k] for k in expected_keys)
    ]

def recursive_clean(base: dict, default: dict):
    """
    מבצע ניקוי מותאם לפי התבנית:
    אם יש רשימה כמו 'services', היא תסונן לפי המבנה שב-template.
    """
    for key, default_value in default.items():
        if isinstance(default_value, dict) and isinstance(base.get(key), dict):
            recursive_clean(base[key], default_value)
        elif isinstance(default_value, list) and isinstance(base.get(key), list):
            base[key] = clean_list_entries_by_template(base[key], default_value)

def ensure_structure(state: dict) -> dict:
    """
    מבטיח שמבנה ה־state תואם בדיוק ל־DEFAULT_STATE_STRUCTURE לפי config בלבד.
    אין שימוש במחרוזות קשיחוֹת.
    """
    recursive_setdefault(state, DEFAULT_STATE_STRUCTURE)
    recursive_clean(state, DEFAULT_STATE_STRUCTURE)
    return state

def fix_values_to_strings(data: dict, template: dict) -> dict:
    """
    מקבלת מילון `data` ומבנה `template`, ומוודאת:
    - כל שדה שמופיע ב-template חייב להיות str ב-data, אחרת מאותחל ל-"".
    - תומך גם בתתי-שדות (רק לעומק 2 כרגע).
    """
    fixed = {}

    for key, expected_value in template.items():
        if isinstance(expected_value, dict):
            inner = data.get(key, {})
            if not isinstance(inner, dict):
                fixed[key] = copy.deepcopy(expected_value)
            else:
                fixed[key] = fix_values_to_strings(inner, expected_value)
        else:
            val = data.get(key)
            fixed[key] = val if isinstance(val, str) else ""

    return fixed

def validate_os(os_dict: dict) -> dict:
    """
    מתקן את שדות os לפי המבנה המוגדר בקונפיג.
    אין שימוש בשמות שדות קשיחים — הכל לפי DEFAULT_STATE_STRUCTURE["target"]["os"]
    """
    os_template = DEFAULT_STATE_STRUCTURE.get("target", {}).get("os", {})
    if not isinstance(os_dict, dict):
        return copy.deepcopy(os_template)

    return fix_values_to_strings(os_dict, os_template)

def validate_services(services: list) -> list:
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

def validate_web_directories(web_dirs: dict) -> dict:
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
        if not has_slash_path:
            valid_paths[""] = ""
        else:
            if "" in valid_paths:
                del valid_paths[""]
                
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

def validate_state_category(state: dict, path: list, validate_fn) -> dict:
    """
    מעדכן קטגוריה בתוך state לפי הפונקציה הנתונה.
    :param state: מילון ה־state המלא
    :param path: רשימת מפתחות שמובילה לשדה (למשל ["target", "os"])
    :param validate_fn: פונקציה שמקבלת dict ומחזירה dict מתוקן
    """
    sub_state = state
    for key in path[:-1]:
        sub_state = sub_state.get(key, {})
        if not isinstance(sub_state, dict):
            return state  # אם מבנה לא תקני, לא נוגעים

    last_key = path[-1]
    value = sub_state.get(last_key)
    if value is not None:
        sub_state[last_key] = validate_fn(value)

    return state

def validate_state(state: dict) -> dict:
    """
    הפונקציה הראשית שמוודאת שה־state במבנה נכון ובעל ערכים תקניים.
    """
    state = ensure_structure(state)

    state = validate_state_category(state, ["target", "os"], validate_os)
    state = validate_state_category(state, ["target", "services"], validate_services)
    state = validate_state_category(state, ["web_directories_status"], validate_web_directories)

    state = truncate_lists(state)
    return state