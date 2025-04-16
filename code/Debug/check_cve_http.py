import json

# טען את כל הנתונים
with open("/mnt/linux-data/project/code/datasets/all_cves_combined.json", encoding="utf-8") as f:
    data = json.load(f)

# ודא שזו רשימה (ולא מפתח בשם CVE_Items)
if not isinstance(data, list):
    data = data.get("CVE_Items", [])

found = 0

for item in data:
    nodes = item.get("configurations", {}).get("nodes", [])
    for node in nodes:
        cpes = []

        # תומך גם ב-cpe_match וגם ב-children
        if "cpe_match" in node:
            cpes.extend(node["cpe_match"])

        if "children" in node:
            for child in node["children"]:
                cpes.extend(child.get("cpe_match", []))

        for match in cpes:
            cpe = match.get("cpe23Uri", "")
            if "http" in cpe.lower():
                print(cpe)
                found += 1

print(f"\n✅ Total CPEs containing 'http': {found}")
