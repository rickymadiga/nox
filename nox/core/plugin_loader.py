import os
import importlib

PLUGIN_DIR = "plugins"


def load_plugins(runtime):

    for item in os.listdir(PLUGIN_DIR):

        path = os.path.join(PLUGIN_DIR, item)

        # skip cache
        if item.startswith("__"):
            continue

        try:

            # folder plugin
            if os.path.isdir(path):

                module = importlib.import_module(f"plugins.{item}.plugin")

            # single file plugin
            elif item.endswith(".py"):

                module_name = item[:-3]
                module = importlib.import_module(f"plugins.{module_name}")

            else:
                continue

            if hasattr(module, "register"):
                module.register(runtime)

            print(f"[PLUGIN] Loaded {item}")

        except Exception as e:
            print(f"[PLUGIN ERROR] {item}: {e}")
            
