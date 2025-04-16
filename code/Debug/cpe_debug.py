import ast

# הטקסט הוא מחרוזת, נהפוך אותו ל-dict
state_str = """{'target': {'ip': '192.168.56.101', 'os': 'Linux', 'services': [{'port': '21', 'protocol': 'tcp', 'service': 'ftp'}, {'port': '22', 'protocol': 'tcp', 'service': 'ssh'}, {'port': '23', 'protocol': 'tcp', 'service': 'telnet'}, {'port': '25', 'protocol': 'tcp', 'service': 'smtp'}, {'port': '53', 'protocol': 'tcp', 'service': 'domain'}, {'port': '80', 'protocol': 'tcp', 'service': 'http'}, {'port': '111', 'protocol': 'tcp', 'service': 'rpcbind'}, {'port': '445', 'protocol': 'tcp', 'service': 'netbios-ssn'}, {'port': '512', 'protocol': 'tcp', 'service': 'exec'}, {'port': '513', 'protocol': 'tcp', 'service': 'login'}, {'port': '1099', 'protocol': 'tcp', 'service': 'java-rmi'}, {'port': '1524', 'protocol': 'tcp', 'service': 'bindshell'}, {'port': '2049', 'protocol': 'tcp', 'service': 'nfs'}, {'port': '2121', 'protocol': 'tcp', 'service': 'ftp'}, {'port': '3306', 'protocol': 'tcp', 'service': 'mysql'}, {'port': '5432', 'protocol': 'tcp', 'service': 'postgresql'}, {'port': '5900', 'protocol': 'tcp', 'service': 'vnc'}, {'port': '6000', 'protocol': 'tcp', 'service': 'x11'}, {'port': '6667', 'protocol': 'tcp', 'service': 'irc'}]}, 'web_directories_status': {'200': {'': ''}, '401': {'': ''}, '403': {'': ''}, '404': {'': ''}, '503': {'': ''}}}"""
state = ast.literal_eval(state_str)  # הופך למילון אמיתי

# קוד לבדיקה מבודדת:
class DummyVulnAgent:
    def generate_possible_cpes(self, state_dict):
        cpes = set()
        target = state_dict.get("target", {})
        os_raw = target.get("os", "").strip().lower()
        if os_raw:
            vendor = os_raw.replace(" ", "_")
            product = os_raw.replace(" ", "_")
            cpes.add(f"cpe:2.3:o:{vendor}:{product}:*:*:*:*:*:*:*:*")

        services = target.get("services", [])
        for s in services:
            name = str(s.get("service", "")).strip().lower().replace(" ", "_")
            if not name:
                continue
            vendor = name
            product = name
            cpes.add(f"cpe:2.3:a:{vendor}:{product}:*:*:*:*:*:*:*:*")
            cpes.add(f"cpe:2.3:a:*:{product}:*:*:*:*:*:*:*:*")
            cpes.add(f"cpe:2.3:a:{vendor}:*:*:*:*:*:*:*:*:*")

        return list(cpes)

if __name__ == "__main__":
    agent = DummyVulnAgent()
    print(agent.generate_possible_cpes(state))
