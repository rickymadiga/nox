import importlib
import os
import logging
from typing import Any

from nox.contracts.plugin import NoxPlugin


logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages loading of subpackage-style plugins (plugins/<name>/plugin.py)
    that inherit from NoxPlugin and implement .load(registry, capabilities).
    """

    def __init__(self, registry: Any, capabilities: Any):
        self.registry = registry
        self.capabilities = capabilities

    def load_plugins(self) -> None:
        """Discover and load all valid subpackage plugins from the 'plugins' directory."""
        plugin_dir = "plugins"

        if not os.path.isdir(plugin_dir):
            logger.warning(f"Plugin directory not found: {plugin_dir}")
            return

        loaded = 0
        skipped = 0
        failed = 0

        for name in os.listdir(plugin_dir):
            path = os.path.join(plugin_dir, name)

            # Only consider directories
            if folder.startswith("__"):
             continue

            plugin_file = os.path.join(path, "plugin.py")

            if not os.path.isfile(plugin_file):
                logger.debug(f"Skipping {name} — no plugin.py found")
                skipped += 1
                continue

            module_path = f"plugins.{name}.plugin"

            try:
                module = importlib.import_module(module_path)

                # Find the first concrete subclass of NoxPlugin
                plugin_class = None
                for attr_name in dir(module):
                    obj = getattr(module, attr_name)
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, NoxPlugin)
                        and obj is not NoxPlugin
                    ):
                        plugin_class = obj
                        break

                if plugin_class is None:
                    logger.warning(f"Skipping {name} — no valid NoxPlugin subclass found")
                    skipped += 1
                    continue

                # Instantiate and load
                plugin_instance = plugin_class()
                plugin_instance.load(self.registry, self.capabilities)

                logger.info(f"Plugin loaded: {name}")
                loaded += 1

            except ImportError as e:
                logger.error(f"Failed to import {module_path}: {e}")
                failed += 1
            except Exception as e:
                logger.error(f"Error loading plugin {name}: {e}", exc_info=True)
                failed += 1

        logger.info(
            f"Plugin loading summary: {loaded} loaded, {skipped} skipped, {failed} failed"
        )


def load_flat_plugins(runtime: Any) -> None:
    """
    Load flat-style plugins (plugins/*.py files) that expose a register(runtime) function.
    This is a separate discovery mechanism — kept for compatibility / mixed plugin styles.
    """
    plugin_dir = "plugins"

    if not os.path.isdir(plugin_dir):
        logger.warning(f"Plugin directory not found: {plugin_dir}")
        return

    loaded = 0
    failed = 0

    for filename in os.listdir(plugin_dir):
        if not filename.endswith(".py"):
            continue
        if filename.startswith(("_", "__")):
            continue
        if filename == "__init__.py":
            continue

        module_name = filename[:-3]
        module_path = f"plugins.{module_name}"

        try:
            module = importlib.import_module(module_path)

            if hasattr(module, "register"):
                module.register(runtime)
                logger.info(f"Flat plugin loaded: {module_name}")
                loaded += 1
            else:
                logger.debug(f"Skipping {module_name} — no register() function")

        except ImportError as e:
            logger.error(f"Failed to import {module_path}: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"Error in flat plugin {module_name}: {e}", exc_info=True)
            failed += 1

    if loaded > 0 or failed > 0:
        logger.info(f"Flat plugins: {loaded} loaded, {failed} failed")


# ────────────────────────────────────────────────
# Convenience entry point (if you want one unified call)
# ────────────────────────────────────────────────

def load_all_plugins(runtime: Any, capabilities: Any = None) -> None:
    """
    Load both subpackage-style (NoxPlugin) and flat-style (register) plugins.
    Use this if your system supports both formats.
    """
    # Subpackage style (class-based)
    manager = PluginManager(runtime, capabilities)
    manager.load_plugins()

    # Flat .py style (function-based)
    load_flat_plugins(runtime)