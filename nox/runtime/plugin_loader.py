import os
import importlib
import traceback
from orchestrator.lily import register as register_lily


def load_plugins(runtime, plugins_path="plugins"):

    # ✅ STEP 1: REGISTER LILY FIRST (CRITICAL)
    try:
        register_lily(runtime)
        print("[CORE] Lily registered ✓")
    except Exception as e:
        print("[CORE ERROR] Failed to register Lily:", e)
        traceback.print_exc()

    # ================================
    # STEP 2: LOAD PLUGINS
    # ================================
    if not os.path.exists(plugins_path):
        print("[PLUGIN LOADER] plugins folder not found")
        return

    for folder in os.listdir(plugins_path):

        plugin_dir = os.path.join(plugins_path, folder)

        # Skip non-dirs
        if not os.path.isdir(plugin_dir):
            continue

        # Skip junk
        if folder.startswith("__") or folder.startswith("."):
            continue

        try:
            module_path = f"{plugins_path}.{folder}.plugin"

            plugin_file = os.path.join(plugin_dir, "plugin.py")
            if not os.path.exists(plugin_file):
                print(f"[PLUGIN SKIP] {folder} (no plugin.py)")
                continue

            module = importlib.import_module(module_path)

            if not hasattr(module, "register"):
                print(f"[PLUGIN SKIP] {folder} (missing register())")
                continue

            module.register(runtime)
            print(f"[PLUGIN] Loaded {folder} ✓")

        except Exception as e:
            print(f"[PLUGIN ERROR] {folder}: {e}")
            traceback.print_exc()