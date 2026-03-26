# nox/contracts/plugin.py

from abc import ABC, abstractmethod


class Plugin(ABC):
    """
    New official plugin contract for Nox system.
    All future plugins should inherit from this.
    """

    name: str
    version: str = "0.1.0"
    description: str = ""

    @abstractmethod
    def load(self, registry):
        """
        Load the plugin into the registry.
        Must be implemented by all plugins.
        """
        pass

    def unload(self):
        """
        Optional cleanup logic.
        Override if needed.
        """
        pass


# -------------------------------------------------------------------
# Backward Compatibility Layer
# -------------------------------------------------------------------

class NoxPlugin:
    """
    Legacy plugin base.
    Kept for compatibility with older Nox modules.
    """

    name = "base_plugin"
    version = "0.1"

    def register(self, registry):
        raise NotImplementedError("Plugins must implement register()")


# -------------------------------------------------------------------
# Adapter (Optional Bridge for Smooth Migration)
# -------------------------------------------------------------------

class LegacyPluginAdapter(Plugin):
    """
    Adapter that allows old NoxPlugin classes
    to behave like the new Plugin contract.
    """

    def __init__(self, legacy_plugin: NoxPlugin):
        self.legacy_plugin = legacy_plugin
        self.name = getattr(legacy_plugin, "name", "legacy_plugin")
        self.version = getattr(legacy_plugin, "version", "0.1")
        self.description = getattr(legacy_plugin, "description", "")

    def load(self, registry):
        self.legacy_plugin.register(registry)

    def unload(self):
        if hasattr(self.legacy_plugin, "unload"):
            self.legacy_plugin.unload()