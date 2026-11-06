"""Deferred imports for heavy optional libraries.

Importing a library like ``stripe`` costs ~40 MB of RAM and ~3 s per Python process, and every
gunicorn worker plus the job worker is its own process. ``lazy_module`` gives a module-level name
that behaves like the module but only imports it on first attribute access, so deployments that
never use the feature (for example billing without ``CLOUD_MODE``) never pay for it.

The proxy keeps ``patch("some.module.stripe")`` and ``patch("some.module.stripe.Webhook.x")``
working in tests, because the name still exists at module level.
"""

import importlib
from types import ModuleType


class LazyModule(ModuleType):
    """Stand-in for a module that is imported on first attribute access."""

    def __init__(self, name: str):
        super().__init__(name)
        self.__dict__['_lazy_target'] = None

    def _load(self) -> ModuleType:
        target = self.__dict__['_lazy_target']
        if target is None:
            target = importlib.import_module(self.__name__)
            self.__dict__['_lazy_target'] = target
        return target

    def __getattr__(self, attr: str):
        # Only called when normal lookup fails, i.e. for attributes of the real module.
        return getattr(self._load(), attr)

    def __setattr__(self, attr: str, value) -> None:
        # ``stripe.api_key = ...`` must set the real module's attribute.
        setattr(self._load(), attr, value)

    def __dir__(self):
        return dir(self._load())


def lazy_module(name: str) -> LazyModule:
    """Return a proxy for ``name`` that imports it on first use."""
    return LazyModule(name)
