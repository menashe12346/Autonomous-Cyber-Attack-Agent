import threading
import subprocess
import os
import time
import re
from agents.base_agent import BaseAgent
from scapy.all import sniff, wrpcap, Raw, TCP

class DefenseAgent(BaseAgent):
    def __init__(self, blackboard_api, output_pcap_path="/tmp/session_capture.pcap"):
        super().__init__(name="DefenseAgent", action_space=[], blackboard_api=blackboard_api)
        self.output_pcap_path = output_pcap_path
        self._stop_event = threading.Event()
        self._sniffer_thread = None
        self._pcap_buffer = []

    def should_run(self):
        return True  # Always runs in background

    def start_background_sniffer(self):
        if self._sniffer_thread is not None and self._sniffer_thread.is_alive():
            return

        def sniff_packets():
            print("[🛡️ DefenseAgent] Starting packet capture...")
            sniff(prn=self._process_packet, store=False, stop_filter=lambda x: self._stop_event.is_set())

        self._sniffer_thread = threading.Thread(target=sniff_packets, daemon=True)
        self._sniffer_thread.start()

    def _process_packet(self, packet):
        try:
            # Save relevant packets (TCP only for simplicity)
            if TCP in packet:
                self._pcap_buffer.append(packet)

                # Detect possible IDS signatures (very simplified)
                if Raw in packet:
                    payload = bytes(packet[Raw].load).decode(errors="ignore").lower()
                    if any(keyword in payload for keyword in ["suricata", "snort", "ids", "alert", "blocked"]):
                        print("[🔍 DefenseAgent] Possible IDS detected in payload!")
                        self._update_state_with_protection("Possible IDS Signature in payload")

        except Exception as e:
            print(f"[⚠️ DefenseAgent] Error processing packet: {e}")

    def _update_state_with_protection(self, message):
        state = self.blackboard_api.get_state_for_agent(self.name)
        protections = state.get("network_protection", [])
        if message not in protections:
            protections.append(message)
        state["network_protection"] = protections
        self.blackboard_api.update_state(self.name, state)

    def finalize_episode(self):
        # עצירת ההקלטה
        self._stop_event.set()
        if self._sniffer_thread:
            self._sniffer_thread.join()

        print(f"[🛑 DefenseAgent] Saving PCAP with {len(self._pcap_buffer)} packets to {self.output_pcap_path}")
        try:
            wrpcap(self.output_pcap_path, self._pcap_buffer)
        except Exception as e:
            print(f"[❌ DefenseAgent] Failed to save PCAP: {e}")

    def run(self):
        # רק בתחילת הריצה
        if not self._sniffer_thread:
            self.start_background_sniffer()
