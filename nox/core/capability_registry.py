# nox/core/capability_index.py

class CapabilityRegistry:
    def __init__(self):
        self.capabilities = {}

    def register(self, plugin_name, capability_list):
        for capability in capability_list:
            capability = capability.lower()

            if capability not in self.capabilities:
                self.capabilities[capability] = []

            if plugin_name not in self.capabilities[capability]:
                self.capabilities[capability].append(plugin_name)

    def find_plugin_from_prompt(self, prompt):
        prompt = prompt.lower()

        for cap, plugins in self.capabilities.items():
            if cap in prompt:
                return plugins[0]

        return None

    def debug_print(self):
        print("\n[CapabilityRegistry]")
        for cap, plugins in self.capabilities.items():
            print(f"{cap} → {plugins}")