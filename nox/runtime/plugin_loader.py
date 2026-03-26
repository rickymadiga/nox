import os
import importlib
import traceback


def load_plugins(runtime, plugins_path="plugins"):

    if not os.path.exists(plugins_path):
        print("[PLUGIN LOADER] plugins folder not found")
        return

    for folder in os.listdir(plugins_path):

        plugin_dir = os.path.join(plugins_path, folder)

        # ✅ Skip non-directories
        if not os.path.isdir(plugin_dir):
            continue

        # ✅ Skip junk folders
        if folder.startswith("__") or folder.startswith("."):
            continue

        try:
            module_path = f"{plugins_path}.{folder}.plugin"

            # ✅ Check plugin.py exists BEFORE import
            plugin_file = os.path.join(plugin_dir, "plugin.py")
            if not os.path.exists(plugin_file):
                print(f"[PLUGIN SKIP] {folder} (no plugin.py)")
                continue

            module = importlib.import_module(module_path)

            # ✅ Validate register
            if not hasattr(module, "register"):
                print(f"[PLUGIN SKIP] {folder} (missing register())")
                continue

            # ✅ SAFE REGISTER
            try:
                module.register(runtime)
                print(f"[PLUGIN] Loaded {folder} ✓")

            except Exception as e:
                print(f"[PLUGIN ERROR] {folder} during register(): {e}")
                traceback.print_exc()

        except Exception as e:
            print(f"[PLUGIN ERROR] {folder}: {e}")
            traceback.print_exc()