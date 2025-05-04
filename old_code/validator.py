"""
def truncate_lists(state: dict, max_services=100, max_paths_per_status=100) -> dict:
    #Limit number of services and paths per status
    state["target"]["services"] = state["target"]["services"][:max_services]
    for code in EXPECTED_STATUS_CODES:
        entries = state["web_directories_status"].get(code, {})
        limited = dict(list(entries.items())[:max_paths_per_status])
        state["web_directories_status"][code] = limited
    return state
"""