"""The classloader provides utilities to dynamically load classes and modules."""

import inspect
import logging
import sys
from importlib import import_module, resources
from importlib.util import find_spec, resolve_name
from types import ModuleType
from typing import Optional, Sequence, Type

from ..core.error import BaseError

LOGGER = logging.getLogger(__name__)


class ModuleLoadError(BaseError):
    """Module load error."""


class ClassNotFoundError(BaseError):
    """Class not found error."""


class ClassLoader:
    """Class used to load classes from modules dynamically."""

    @classmethod
    def load_module(
        cls, mod_path: str, package: Optional[str] = None
    ) -> Optional[ModuleType]:
        """Load a module by its absolute path.

        Args:
            mod_path: the absolute or relative module path
            package: the parent package to search for the module

        Returns:
            The resolved module or `None` if the module cannot be found

        Raises:
            ModuleLoadError: If there was an error loading the module

        """

        if package:
            # preload parent package
            if not cls.load_module(package):
                return None
            # must treat as a relative import
            if not mod_path.startswith("."):
                mod_path = f".{mod_path}"

        full_path = resolve_name(mod_path, package)

        if full_path in sys.modules:
            return sys.modules[full_path]

        if "." in mod_path:
            parent_mod_path, mod_name = mod_path.rsplit(".", 1)
            if parent_mod_path and parent_mod_path[-1] != ".":
                parent_mod = cls.load_module(parent_mod_path, package)
                if not parent_mod:
                    return None
                package = parent_mod.__name__
                mod_path = f".{mod_name}"

        # Load the module spec first
        # this means that a later ModuleNotFoundError indicates a code issue
        spec = find_spec(mod_path, package)
        if not spec:
            return None

        try:
            return import_module(mod_path, package)
        except ModuleNotFoundError as e:
            LOGGER.warning("Module %s not found during import", full_path)
            raise ModuleLoadError(f"Unable to import module {full_path}: {str(e)}") from e

    @classmethod
    def load_class(
        cls,
        class_name: str,
        default_module: Optional[str] = None,
        package: Optional[str] = None,
    ):
        """Resolve a complete class path (ie. typing.Dict) to the class itself.

        Args:
            class_name: the class name
            default_module: the default module to load, if not part of in the class name
            package: the parent package to search for the module

        Returns:
            The resolved class

        Raises:
            ClassNotFoundError: If the class could not be resolved at path
            ModuleLoadError: If there was an error loading the module

        """

        if "." in class_name:
            # import module and find class
            mod_path, class_name = class_name.rsplit(".", 1)
        elif default_module:
            mod_path = default_module
        else:
            LOGGER.warning(
                "Cannot resolve class name %s with no default module", class_name
            )
            raise ClassNotFoundError(
                f"Cannot resolve class name with no default module: {class_name}"
            )

        mod = cls.load_module(mod_path, package)
        if not mod:
            LOGGER.warning(
                "Module %s not found when loading class %s", mod_path, class_name
            )
            raise ClassNotFoundError(f"Module '{mod_path}' not found")

        resolved = getattr(mod, class_name, None)
        if not resolved:
            LOGGER.warning("Class %s not found in module %s", class_name, mod_path)
            raise ClassNotFoundError(
                f"Class '{class_name}' not defined in module: {mod_path}"
            )
        if not isinstance(resolved, type):
            LOGGER.warning(
                "Resolved attribute %s in module %s is not a class", class_name, mod_path
            )
            raise ClassNotFoundError(
                f"Resolved value is not a class: {mod_path}.{class_name}"
            )
        LOGGER.debug("Successfully loaded class %s from module %s", class_name, mod_path)
        return resolved

    @classmethod
    def load_subclass_of(
        cls, base_class: Type, mod_path: str, package: Optional[str] = None
    ):
        """Resolve an implementation of a base path within a module.

        Args:
            base_class: the base class being implemented
            mod_path: the absolute module path
            package: the parent package to search for the module

        Returns:
            The resolved class

        Raises:
            ClassNotFoundError: If the module or class implementation could not be found
            ModuleLoadError: If there was an error loading the module

        """

        mod = cls.load_module(mod_path, package)
        if not mod:
            LOGGER.warning(
                "Module %s not found when loading subclass of %s",
                mod_path,
                base_class.__name__,
            )
            raise ClassNotFoundError(f"Module '{mod_path}' not found")

        # Find the first declared class that inherits from the base_class
        try:
            imported_class = next(
                obj
                for name, obj in inspect.getmembers(mod, inspect.isclass)
                if issubclass(obj, base_class) and obj is not base_class
            )
        except StopIteration:
            LOGGER.debug(
                "No subclass of %s found in module %s",
                base_class.__name__,
                mod_path,
            )
            raise ClassNotFoundError(
                f"Could not resolve a class that inherits from {base_class}"
            ) from None
        return imported_class

    @classmethod
    def scan_subpackages(cls, package: str) -> Sequence[str]:
        """Return a list of sub-packages defined under a named package."""
        LOGGER.debug("Scanning subpackages under package %s", package)
        if "." in package:
            package, sub_pkg = package.split(".", 1)
            LOGGER.debug("Extracted main package: %s, sub-package: %s", package, sub_pkg)
        else:
            sub_pkg = "."
            LOGGER.debug("No sub-package provided, defaulting to %s", sub_pkg)

        try:
            package_path = resources.files(package)
        except FileNotFoundError:
            LOGGER.warning("Package %s not found during subpackage scan", package)
            raise ModuleLoadError(f"Undefined package {package}")

        if not (package_path / sub_pkg).is_dir():
            LOGGER.warning("Sub-package %s is not a directory under %s", sub_pkg, package)
            raise ModuleLoadError(f"Undefined package {package}")

        found = []
        joiner = "" if sub_pkg == "." else f"{sub_pkg}."
        sub_path = package_path / sub_pkg
        for item in sub_path.iterdir():
            if (item / "__init__.py").exists():
                subpackage = f"{package}.{joiner}{item.name}"
                found.append(subpackage)
        LOGGER.debug("%d sub-packages found under %s: %s", len(found), package, found)
        return found


class DeferLoad:
    """Helper to defer loading of a class definition."""

    _class_cache = {}  # Shared cache for resolved classes

    def __init__(self, cls_path: str):
        """Initialize the `DeferLoad` instance with a qualified class path."""
        self._cls_path = cls_path

    def __call__(self, *args, **kwargs):
        """Magic method to call the `DeferLoad` as a function."""
        return self.resolved(*args, **kwargs)

    @property
    def resolved(self):
        """Accessor for the resolved class instance."""
        if self._cls_path not in DeferLoad._class_cache:
            DeferLoad._class_cache[self._cls_path] = ClassLoader.load_class(
                self._cls_path
            )
        return DeferLoad._class_cache[self._cls_path]
