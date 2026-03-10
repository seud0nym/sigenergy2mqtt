"""update_en_translation.py

Extracts translatable strings from the sigenergy2mqtt Python source tree via
AST analysis, writes the canonical English YAML file (en.yaml), and propagates
new / changed keys to every other language file in the translations directory.

Usage
-----
    python update_en_translation.py

The script is designed to be idempotent: running it multiple times produces the
same result as running it once.

Key responsibilities
--------------------
1. ``TranslationExtractor``  – walks all ``.py`` files and collects sensor name,
   option, and alarm-bit strings from ``super().__init__()`` calls and ``_t()``
   helper invocations.
2. ``CLIHelpExtractor``       – collects ``help=`` text from ``argparse``
   ``add_argument()`` calls in ``config/cli.py``.
3. ``propagate_translations`` – applies single-pass inheritance using a
   topological sort so each class sees its ancestor data exactly once.
4. ``propagate_to_other_translations`` – synchronises every non-English YAML
   file: adds missing keys, prunes obsolete keys, and re-translates
   ``name_reset`` entries where a language-specific template is available.
"""

from __future__ import annotations

import ast
import logging
import re
import threading
import warnings
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import overload

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# YAML configuration
# ---------------------------------------------------------------------------

_yaml_local = threading.local()


def get_yaml() -> YAML:
    if getattr(_yaml_local, "parser", None) is None:
        parser = YAML()
        parser.indent(mapping=2, sequence=4, offset=2)
        parser.preserve_quotes = True
        parser.width = 1000  # Avoid line-wrapping
        _yaml_local.parser = parser
    return _yaml_local.parser


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Language codes that have a known template for the "reset" action.
RESET_TRANSLATIONS: dict[str, str] = {
    "de": "Setze {name}",
    "es": "Establecer {name}",
    "fr": "Régler {name}",
    "it": "Imposta {name}",
    "ja": "{name}を設定",
    "ko": "{name} 설정",
    "nl": "Stel {name} in",
    "pt": "Definir {name}",
    "zh-Hans": "設置 {name}",
}

#: Classes whose ``__init__`` first positional argument is a *type*, not a
#: name, so the name lives at index 1 instead of 0.
MODBUS_BASE_CLASSES: frozenset[str] = frozenset({"ModbusDevice", "Inverter", "ACCharger", "DCCharger", "ESS", "PVString", "PowerPlant", "GridSensor", "GridCode"})

#: Classes that are infrastructure/base devices – their ``name`` field is
#: typically dynamic and should not be emitted as a static translation.
IGNORE_NAME_CLASSES: frozenset[str] = frozenset({"Device", "ModbusDevice", "Service"})

#: Classes whose subclasses automatically receive a ``name_reset`` entry.
RESETTABLE_BASE_CLASSES: frozenset[str] = frozenset({"ResettableAccumulationSensor", "EnergyDailyAccumulationSensor", "EnergyLifetimeAccumulationSensor"})

#: Hard-coded fallback names for classes whose names are fully dynamic at
#: runtime and cannot be inferred from the AST alone.
DYNAMIC_CLASS_NAMES: dict[str, str] = {
    "Inverter": "{model_id} {serial}",
    "ESS": "{model_id} {serial_number} ESS",
    "PVString": "{model_id} {serial_number} PV String {string_number}",
}

#: Placeholder-like tokens that indicate a string has not yet been resolved to
#: a concrete value.
_UNRESOLVED_TOKENS: frozenset[str] = frozenset({"{words}", "{name}", "{}"})

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def is_placeholder_only(s: object) -> bool:
    """Return *True* if *s* consists solely of ``{placeholder}`` tokens.

    Strings like ``"{name}"`` or ``"{model_id} {serial}"`` are considered
    placeholder-only.  Strings that contain any alphanumeric characters
    outside of placeholders (e.g. ``"Set {name}"``) return *False*.

    Parameters
    ----------
    s:
        Value to test.  Non-string values always return *False*.
    """
    if not isinstance(s, str):
        return False
    if "{" not in s or "}" not in s:
        return False
    remaining = re.sub(r"\{[^{}]+\}", "", s)
    return not bool(re.search(r"[a-zA-Z0-9]", remaining))


@overload
def sort_dict(d: dict) -> dict: ...


@overload
def sort_dict(d: list) -> list: ...


def sort_dict(d: dict | list) -> dict | list:
    """Recursively sort a nested *dict* / *list* structure by key.

    Integer-looking keys are sorted numerically before string keys so that
    alarm-bit dictionaries (``{"0": "...", "1": "...", "10": "..."}``) sort
    in natural order.

    Parameters
    ----------
    d:
        The data structure to sort.  Non-dict / non-list values are returned
        unchanged.
    """

    def _key(k: object) -> tuple:
        try:
            return (0, int(str(k)))
        except (ValueError, TypeError):
            return (1, str(k))

    if isinstance(d, dict):
        return {k: sort_dict(v) for k, v in sorted(d.items(), key=lambda x: _key(x[0]))}
    if isinstance(d, list):
        return [sort_dict(i) for i in d]
    return d


def prune_empty_dicts(d: dict | object) -> dict | object:
    """Recursively remove empty dicts, *None* values, and blank strings in-place.

    Empty-dict detection happens *after* recursing into children so that
    dictionaries that become empty as a result of pruning their own children
    are also removed.

    Parameters
    ----------
    d:
        Root of the structure to prune.  Non-dict values are returned as-is.

    Returns
    -------
    object
        The pruned structure (same object for dicts, unchanged for scalars).
    """
    if not isinstance(d, dict):
        return d

    to_delete: list[str] = []
    for k, v in d.items():
        if isinstance(v, dict):
            # Recurse first so children are pruned before we test emptiness.
            d[k] = prune_empty_dicts(v)
            if not d[k]:
                to_delete.append(k)
        elif v is None or (isinstance(v, str) and not v.strip()):
            to_delete.append(k)

    for k in to_delete:
        del d[k]

    return d


@overload
def _to_commented(obj: dict) -> CommentedMap: ...


@overload
def _to_commented(obj: list) -> CommentedSeq: ...


@overload
def _to_commented(obj: object) -> object: ...


def _to_commented(obj: object) -> object:
    """Recursively convert a plain dict/list tree to ``ruamel.yaml`` comment-aware types.

    This allows ``ruamel.yaml`` to round-trip the structure while preserving
    any inline YAML comments that were present in the original file.

    Parameters
    ----------
    obj:
        A plain Python dict, list, or scalar value.
    """
    if isinstance(obj, dict):
        return CommentedMap({k: _to_commented(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return CommentedSeq([_to_commented(i) for i in obj])
    return obj


@overload
def _strip_comments(obj: dict) -> dict: ...


@overload
def _strip_comments(obj: list) -> list: ...


@overload
def _strip_comments(obj: object) -> object: ...


def _strip_comments(obj: object) -> object:
    """Return a plain (non-``CommentedMap``) copy of a ``ruamel.yaml`` object.

    Parameters
    ----------
    obj:
        A ``CommentedMap``, ``CommentedSeq``, or scalar loaded by
        ``ruamel.yaml``.
    """
    if isinstance(obj, dict):
        return {k: _strip_comments(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_comments(i) for i in obj]
    return obj


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def get_ast_string_values(node: ast.expr | None) -> list[str]:
    """Extract all concrete string values reachable from an AST expression node.

    Handles the following expression forms:

    * ``ast.Constant`` (plain string literal)
    * ``ast.JoinedStr`` (f-string) – simple variable or attribute interpolations
      are rendered as ``{var}`` placeholders
    * ``ast.IfExp`` – both branches are returned
    * ``ast.BinOp`` with ``+`` – string concatenation is collapsed
    * ``ast.List`` – all element strings are returned flat
    * ``ast.Call`` for ``" ".join(words)``-style expressions

    Unknown / unsupported node types emit a *debug* log message and return
    an empty list so callers can distinguish "nothing found" from an error.

    Parameters
    ----------
    node:
        The AST expression node to evaluate.

    Returns
    -------
    list[str]
        Zero or more concrete string values extracted from *node*.
    """
    if node is None:
        return []

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]

    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for val in node.values:
            if isinstance(val, ast.Constant):
                parts.append(str(val.value))
            elif isinstance(val, ast.FormattedValue):
                inner = val.value
                if isinstance(inner, ast.Name):
                    parts.append(f"{{{inner.id}}}")
                elif isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Name):
                    parts.append(f"{{{inner.value.id}.{inner.attr}}}")
                elif isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) and inner.func.attr == "lower" and isinstance(inner.func.value, ast.Name):
                    parts.append(f"{{{inner.func.value.id}}}")
                elif isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Attribute) and inner.attr == "__name__" and inner.value.attr == "__class__":
                    parts.append("{self}")
                else:
                    found = [n.id for n in ast.walk(inner) if isinstance(n, ast.Name)]
                    clean = [n for n in found if n != "self"]
                    parts.append(f"{{{(clean or found)[0]}}}" if (clean or found) else "{}")
        return ["".join(parts)]

    if isinstance(node, ast.IfExp):
        return get_ast_string_values(node.body) + get_ast_string_values(node.orelse)

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = get_ast_string_values(node.left)
        right = get_ast_string_values(node.right)
        if left and right:
            return [l + r for l in left for r in right]  # noqa: E741
        return left or right

    if isinstance(node, ast.List):
        result: list[str] = []
        for elt in node.elts:
            result.extend(get_ast_string_values(elt))
        return result

    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "join" and isinstance(func.value, ast.Constant) and isinstance(func.value.value, str) and node.args:
            sep = func.value.value
            vals = get_ast_string_values(node.args[0])
            if vals:
                return [sep.join(vals)]
            found = [n.id for n in ast.walk(node.args[0]) if isinstance(n, ast.Name)]
            if found:
                return [f"{{{found[0]}}}"]

    log.debug("get_ast_string_values: unsupported node type %s", type(node).__name__)
    return []


# ---------------------------------------------------------------------------
# Topological sort for class inheritance
# ---------------------------------------------------------------------------


def topological_sort(class_bases: dict[str, list[str]]) -> list[str]:
    """Return classes in topological order (parents before children).

    Uses Kahn's algorithm.  Cycles are detected and result in a *warning*;
    remaining nodes are appended in arbitrary order so processing can
    continue.

    Parameters
    ----------
    class_bases:
        Mapping of ``{class_name: [direct_parent, ...]}`` as populated by
        ``TranslationExtractor``.

    Returns
    -------
    list[str]
        All class names present in *class_bases* sorted so that every class
        appears after all of its known parents.
    """
    all_classes: set[str] = set(class_bases.keys())
    for bases in class_bases.values():
        all_classes.update(bases)

    # Build in-degree count and adjacency list (parent → children).
    in_degree: dict[str, int] = {c: 0 for c in all_classes}
    children: dict[str, list[str]] = {c: [] for c in all_classes}

    for cls, bases in class_bases.items():
        for base in bases:
            if base in all_classes:
                in_degree[cls] += 1
                children[base].append(cls)

    queue: deque[str] = deque(c for c in all_classes if in_degree[c] == 0)
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for child in children[node]:
            in_degree[child] -= 1
            if in_degree[child] == 0:
                queue.append(child)

    remaining = [c for c in all_classes if in_degree[c] > 0]
    if remaining:
        warnings.warn(
            f"Cycle detected in class_bases involving: {remaining}. Appending in arbitrary order.",
            stacklevel=2,
        )
        order.extend(remaining)

    return order


# ---------------------------------------------------------------------------
# Shared propagation logic
# ---------------------------------------------------------------------------


def propagate_translations(data: dict, class_bases: dict[str, list[str]]) -> None:
    """Propagate inherited ``options``, ``attributes``, ``alarm``, and ``name`` entries.

    Iterates classes in topological order (parents before children) so that
    each class only needs a single pass to receive all ancestor data.
    Missing keys are copied from the parent; existing keys are not overwritten.

    Parameters
    ----------
    data:
        The translation dict keyed by class name, modified in-place.
    class_bases:
        Mapping of ``{class_name: [direct_parent, ...]}`` as populated by
        ``TranslationExtractor``.
    """
    for cls in topological_sort(class_bases):
        if cls not in class_bases:
            continue
        for base in class_bases[cls]:
            if base not in data:
                continue
            data.setdefault(cls, {})
            for key in ("options", "attributes", "alarm", "name"):
                if key not in data[base]:
                    continue
                base_val = data[base][key]
                if key not in data[cls]:
                    data[cls][key] = base_val.copy() if isinstance(base_val, dict) else base_val
                elif isinstance(base_val, dict) and isinstance(data[cls][key], dict):
                    for subkey, subval in base_val.items():
                        data[cls][key].setdefault(subkey, subval)


# ---------------------------------------------------------------------------
# AST visitor – sensor translations
# ---------------------------------------------------------------------------


class TranslationExtractor(ast.NodeVisitor):
    """Walk Python source files and collect translatable sensor strings.

    After calling ``visit()`` on one or more AST trees, the results are
    available in ``self.translations`` (keyed by class name) and
    ``self.class_bases`` (maps each class to its direct base classes).

    The visitor tracks:

    * Sensor *name* strings from ``super().__init__(name=...)`` calls.
    * *name_on* / *name_off* overrides.
    * *options* lists.
    * Alarm bit descriptions from ``match`` / ``case`` blocks.
    * ``_t("ClassName.key", "default")`` explicit translation registrations.
    * Whether a class inherits from a resettable accumulation sensor so that
      an automatic ``name_reset`` entry can be generated.
    """

    def __init__(self) -> None:
        self.translations: dict[str, dict] = {}
        self.class_bases: dict[str, list[str]] = {}
        self._current_class: str | None = None
        self._is_resettable: bool = False
        self._local_vars: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_resettable_class(self, bases: list[str]) -> bool:
        """Return *True* if any base class is a known resettable type.

        Checks both direct base names and the full resolved ancestry stored in
        ``self.class_bases``.

        Parameters
        ----------
        bases:
            Direct parent class names of the class being evaluated.
        """
        if any(b in RESETTABLE_BASE_CLASSES for b in bases):
            return True
        # Walk one more level of known bases.
        for b in bases:
            if any(grandparent in RESETTABLE_BASE_CLASSES for grandparent in self.class_bases.get(b, [])):
                return True
        return False

    def _has_ancestor(self, cls: str, targets: frozenset[str]) -> bool:
        """Return *True* if *cls* has any class in *targets* in its ancestry.

        Performs a BFS over ``self.class_bases`` for the full inheritance
        chain so that indirect descendants are handled correctly.

        Parameters
        ----------
        cls:
            Class whose ancestry to search.
        targets:
            Set of class names to look for.
        """
        visited: set[str] = set()
        queue: deque[str] = deque([cls])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            for base in self.class_bases.get(current, []):
                if base in targets:
                    return True
                queue.append(base)
        return False

    def _add_translation(self, cls: str, key: str, value: str) -> None:
        """Store a translation entry for *cls* under *key* if *value* is concrete.

        Parameters
        ----------
        cls:
            Class name (top-level key in the translation dict).
        key:
            Sub-key such as ``"name"``, ``"name_reset"``, etc.
        value:
            The English string value.  Placeholder-only values are silently
            discarded.
        """
        if is_placeholder_only(value):
            return
        self.translations.setdefault(cls, {})[key] = value

    def _add_attr(self, cls: str, attr: str, value: str) -> None:
        """Store an attribute translation for *cls*.

        Entries are nested under ``translations[cls]["attributes"]``.
        The special key ``"since-protocol"`` is ignored because it is not a
        user-visible string.

        Parameters
        ----------
        cls:
            Class name.
        attr:
            Attribute name (e.g. ``"comment"`` or ``"source"``).
        value:
            English attribute value string.
        """
        if attr == "since-protocol" or is_placeholder_only(value):
            return
        self.translations.setdefault(cls, {}).setdefault("attributes", {})[attr] = value

    def _add_alarm(self, cls: str, bit: str, value: str) -> None:
        """Store an alarm-bit description for *cls*.

        Entries are nested under ``translations[cls]["alarm"]``.

        Parameters
        ----------
        cls:
            Class name.
        bit:
            String representation of the bit integer (e.g. ``"3"``).
        value:
            Human-readable alarm description.
        """
        if is_placeholder_only(value):
            return
        self.translations.setdefault(cls, {}).setdefault("alarm", {})[bit] = value

    # ------------------------------------------------------------------
    # Class / function scope tracking
    # ------------------------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track the current class and record direct base classes."""
        prev_class = self._current_class
        prev_resettable = self._is_resettable

        self._current_class = node.name
        bases: list[str] = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute) and isinstance(base.attr, str):
                bases.append(base.attr)

        if bases:
            self.class_bases[node.name] = bases
        self._is_resettable = self._is_resettable_class(bases)

        self.generic_visit(node)
        self._current_class = prev_class
        self._is_resettable = prev_resettable

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # type: ignore[override]
        """Reset local variable tracking for each function scope."""
        prev_vars = self._local_vars
        self._local_vars = {}
        self.generic_visit(node)
        self._local_vars = prev_vars

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Call visitors
    # ------------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        """Dispatch ``super().__init__()`` and ``_t()`` call handlers."""
        if not self._current_class:
            self.generic_visit(node)
            return

        if self._is_super_init(node):
            self._handle_super_init(node)
        elif self._is_t_call(node):
            self._handle_t_call(node)

        self.generic_visit(node)

    @staticmethod
    def _is_super_init(node: ast.Call) -> bool:
        """Return *True* if *node* represents a ``super().__init__(...)`` call."""
        return (
            isinstance(node.func, ast.Attribute) and node.func.attr == "__init__" and isinstance(node.func.value, ast.Call) and isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == "super"
        )

    @staticmethod
    def _is_t_call(node: ast.Call) -> bool:
        """Return *True* if *node* is a ``_t("key", "default")`` call."""
        return isinstance(node.func, ast.Name) and node.func.id == "_t"

    def _resolve_name_arg(self, node: ast.Call) -> str | None:
        """Resolve the sensor name from a ``super().__init__()`` call.

        Checks keyword arguments first, then falls back to positional
        arguments.  Uses ``self._local_vars`` for variables assigned earlier
        in the same function body.  If the resolved value is a known
        placeholder the class-specific fallback from ``DYNAMIC_CLASS_NAMES``
        is used instead.

        Parameters
        ----------
        node:
            The ``super().__init__(...)`` call node.

        Returns
        -------
        str | None
            The resolved name string, or *None* if it could not be determined.
        """
        # 1. Keyword argument `name=`
        for kw in node.keywords:
            if kw.arg == "name":
                names = get_ast_string_values(kw.value)
                return names[0] if names else None

        # 2. Positional argument – index depends on whether this class
        #    (or any ancestor) is a ModbusDevice subclass.
        assert self._current_class is not None
        arg_index = 1 if self._has_ancestor(self._current_class, MODBUS_BASE_CLASSES) else 0

        if len(node.args) <= arg_index:
            return None

        arg_node = node.args[arg_index]

        # Try local variable resolution first.
        if isinstance(arg_node, ast.Name) and arg_node.id in self._local_vars:
            name = self._local_vars[arg_node.id]
        else:
            values = get_ast_string_values(arg_node)
            name = values[0] if values else None

        # Apply per-class dynamic fallbacks.
        if not name or name in _UNRESOLVED_TOKENS:
            name = DYNAMIC_CLASS_NAMES.get(self._current_class, name)

        # Last resort: try the 5th positional argument (model name) for
        # ModbusDevice subclasses.
        if (not name or name in _UNRESOLVED_TOKENS) and len(node.args) > 4:
            model_vals = get_ast_string_values(node.args[4])
            if model_vals:
                name = model_vals[0]

        return name if name and name not in _UNRESOLVED_TOKENS else None

    def _handle_super_init(self, node: ast.Call) -> None:
        """Process a ``super().__init__(...)`` call.

        Extracts and stores the sensor name, ``name_on`` / ``name_off``
        overrides, the ``options`` list, and (if applicable) the
        ``name_reset`` string.

        Parameters
        ----------
        node:
            The ``super().__init__(...)`` call node.
        """
        assert self._current_class is not None

        # name_on / name_off
        for kw in node.keywords:
            if kw.arg in ("name_on", "name_off"):
                vals = get_ast_string_values(kw.value)
                if vals:
                    self._add_translation(self._current_class, kw.arg, vals[0])

        # options=[...]
        for kw in node.keywords:
            if kw.arg == "options" and isinstance(kw.value, ast.List):
                self._extract_options(self._current_class, kw.value)

        if self._current_class in IGNORE_NAME_CLASSES:
            return

        name = self._resolve_name_arg(node)
        if name:
            self._add_translation(self._current_class, "name", name)
            if self._is_resettable:
                self._add_translation(self._current_class, "name_reset", f"Set {name}")

    def _handle_t_call(self, node: ast.Call) -> None:
        """Process a ``_t("ClassName.key", "default")`` explicit registration.

        Parameters
        ----------
        node:
            The ``_t(...)`` call node.
        """
        assert self._current_class is not None
        if len(node.args) < 2:
            return

        keys = get_ast_string_values(node.args[0])
        defaults = get_ast_string_values(node.args[1])
        if not keys or not defaults:
            return

        key = keys[0].replace("{self}", self._current_class).replace("{}", self._current_class)
        default = defaults[0]

        if key.startswith(f"{self._current_class}."):
            sub_key = key[len(self._current_class) + 1 :]
            self._add_translation(self._current_class, sub_key, default)
        elif "." not in key:
            self._add_translation(self._current_class, key, default)

    def _extract_options(self, cls: str, list_node: ast.List) -> None:
        """Parse an ``options=[...]`` literal and store each non-empty entry.

        Parameters
        ----------
        cls:
            Target class name.
        list_node:
            The ``ast.List`` node containing option string elements.
        """
        options: dict[str, str] = {}
        for i, elt in enumerate(list_node.elts):
            vals = get_ast_string_values(elt)
            if vals and vals[0].strip():
                options[str(i)] = vals[0]
        if options:
            self.translations.setdefault(cls, {})["options"] = options

    # ------------------------------------------------------------------
    # Assignment visitor
    # ------------------------------------------------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        """Extract translations from attribute / subscript assignments.

        Handles the following patterns:

        * ``self["options"] = [...]``
        * ``self["comment"] = "..."``
        * ``attributes["somekey"] = "..."``
        * ``name = "..."``  (local variable, used for deferred resolution)
        * ``self.name = "..."``
        * ``self["name"] = "..."``
        """
        if not self._current_class:
            self.generic_visit(node)
            return

        for target in node.targets:
            self._process_assign_target(target, node.value)

        self.generic_visit(node)

    def _process_assign_target(self, target: ast.expr, value: ast.expr) -> None:
        """Dispatch a single assignment target to the appropriate handler.

        Parameters
        ----------
        target:
            The LHS node of the assignment.
        value:
            The RHS node of the assignment.
        """
        assert self._current_class is not None

        if isinstance(target, ast.Attribute):
            if target.attr == "name" and isinstance(target.value, ast.Name) and target.value.id == "self":
                vals = get_ast_string_values(value)
                if vals and self._current_class not in IGNORE_NAME_CLASSES and not is_placeholder_only(vals[0]):
                    self._add_translation(self._current_class, "name", vals[0])
            return

        if not isinstance(target, ast.Subscript):
            # Plain name assignment – track as local variable.
            if isinstance(target, ast.Name):
                vals = get_ast_string_values(value)
                if vals:
                    self._local_vars[target.id] = vals[0]
            return

        subscript_val = target.value
        slice_node = target.slice

        if not isinstance(slice_node, ast.Constant) or not isinstance(slice_node.value, str):
            return

        slice_key: str = slice_node.value

        # self["..."] = ...
        if isinstance(subscript_val, ast.Name) and subscript_val.id == "self":
            if slice_key == "options" and isinstance(value, ast.List):
                self._extract_options(self._current_class, value)
            elif slice_key == "comment":
                vals = get_ast_string_values(value)
                if vals:
                    self._add_attr(self._current_class, "comment", vals[0])
            elif slice_key == "name" and self._current_class not in IGNORE_NAME_CLASSES:
                vals = get_ast_string_values(value)
                if vals and not is_placeholder_only(vals[0]):
                    self._add_translation(self._current_class, "name", vals[0])

        # attributes["..."] = ...
        elif isinstance(subscript_val, ast.Name) and subscript_val.id == "attributes":
            vals = get_ast_string_values(value)
            if vals:
                self._add_attr(self._current_class, slice_key, vals[0])

    # ------------------------------------------------------------------
    # Match / case visitor (alarm bit decoding)
    # ------------------------------------------------------------------

    def _handle_match_case(self, node: object) -> None:
        """Extract alarm-bit descriptions from ``match`` / ``case`` blocks.

        Only ``case <integer>:`` arms whose body is a single ``return "..."``
        statement are processed.

        Parameters
        ----------
        node:
            A ``match_case`` AST node (``ast.match_case`` in Python 3.10+).
        """
        if not self._current_class:
            return

        pattern = getattr(node, "pattern", None)
        body = getattr(node, "body", [])

        if not isinstance(pattern, ast.MatchValue) or not isinstance(pattern.value, ast.Constant):
            return

        bit_val = pattern.value.value
        if not isinstance(bit_val, int):
            return

        bit = str(bit_val)
        for body_node in body:
            if isinstance(body_node, ast.Return):
                names = get_ast_string_values(body_node.value)
                if names and names[0].strip():
                    self._add_alarm(self._current_class, bit, names[0])

    def visit_match_case(self, node: object) -> None:  # type: ignore[override]
        """Visit a ``match_case`` node (Python 3.10+)."""
        self._handle_match_case(node)
        self.generic_visit(node)  # type: ignore[arg-type]

    # Alias for older AST node naming.
    visit_MatchCase = visit_match_case  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# AST visitor – CLI help text
# ---------------------------------------------------------------------------


class CLIHelpExtractor(ast.NodeVisitor):
    """Extract ``help=`` text from ``argparse`` ``add_argument()`` calls.

    After calling ``visit()`` the results are available in
    ``self.cli_translations``, a dict of the form::

        {
            "dest_value": {"help": "Help string"},
            ...
        }
    """

    def __init__(self) -> None:
        self.cli_translations: dict[str, dict[str, str]] = {}

    def visit_Call(self, node: ast.Call) -> None:
        """Record ``dest`` / ``help`` pairs from ``add_argument()`` calls."""
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"):
            self.generic_visit(node)
            return

        dest: str | None = None
        help_text: str | None = None

        for kw in node.keywords:
            if kw.arg == "dest":
                vals = get_ast_string_values(kw.value)
                dest = vals[0] if vals else (kw.value.attr if isinstance(kw.value, ast.Attribute) else None)
            elif kw.arg == "help":
                vals = get_ast_string_values(kw.value)
                if vals:
                    help_text = vals[0]

        if dest and help_text:
            self.cli_translations[dest] = {"help": help_text}

        self.generic_visit(node)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def extract_cli_help(config_cli_path: Path) -> dict[str, dict[str, str]]:
    """Parse *config_cli_path* and return argparse help strings.

    Parameters
    ----------
    config_cli_path:
        Path to the ``config/cli.py`` file containing ``add_argument()``
        calls.

    Returns
    -------
    dict
        Mapping of ``{dest: {"help": "..."}}`` for each discovered argument.
    """
    extractor = CLIHelpExtractor()
    extractor.visit(ast.parse(config_cli_path.read_text(encoding="utf-8")))
    return extractor.cli_translations


def load_yaml(path: Path) -> dict:
    """Load a YAML file and return its content as a plain Python dict.

    Returns an empty dict if the file does not exist.

    Parameters
    ----------
    path:
        Path to the YAML file.
    """
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return get_yaml().load(fh) or {}


def save_yaml(path: Path, data: object) -> None:
    """Write *data* to *path* using a thread-local ``YAML`` parser.

    Parameters
    ----------
    path:
        Destination file path.
    data:
        A ``CommentedMap`` / ``CommentedSeq`` tree or plain Python structure.
    """
    with path.open("w", encoding="utf-8") as fh:
        get_yaml().dump(data, fh)


# ---------------------------------------------------------------------------
# Deep merge helpers
# ---------------------------------------------------------------------------


def merge_translations(base: dict, new: dict) -> None:
    """Recursively merge *new* into *base*, overwriting existing scalar values.

    Unlike ``dict.update``, this recurses into nested dicts rather than
    replacing them wholesale.

    Parameters
    ----------
    base:
        Target dict, modified in-place.
    new:
        Source dict whose values take precedence.
    """
    for key, value in new.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            merge_translations(base[key], value)
        else:
            base[key] = value


def deep_update_commented(target: dict, source: dict) -> dict:
    """Update *target* (``CommentedMap``) from *source* (plain dict).

    Preserves inline YAML comments on unchanged scalar values.  Keys present
    in *target* but absent from *source* are **removed** so the output
    exactly mirrors *source*.

    Parameters
    ----------
    target:
        A ``CommentedMap`` loaded from the existing YAML file.
    source:
        The newly-computed plain dict to synchronise *target* with.

    Returns
    -------
    dict
        *target*, updated in-place.
    """
    if not isinstance(target, dict) or not isinstance(source, dict):
        return source

    # Remove stale keys.
    for k in [k for k in target if k not in source]:
        del target[k]

    for k, v in source.items():
        if k in target:
            if isinstance(v, dict) and isinstance(target[k], dict):
                deep_update_commented(target[k], v)
            elif target[k] != v:
                target[k] = v
        else:
            target[k] = v

        if hasattr(target, "move_to_end"):
            getattr(target, "move_to_end")(k)

    return target


# ---------------------------------------------------------------------------
# Safety-net backfill
# ---------------------------------------------------------------------------


def preserve_existing_sections(new_translations: dict, old_translations: dict | None) -> None:
    """Backfill *options* and *alarm* entries that are missing from extraction.

    This is a safety net for temporary gaps in AST extraction: if the old
    English YAML had an ``options`` or ``alarm`` section for a class but the
    current extraction missed it, the old values are carried forward so they
    are not silently deleted.

    This function does **not** overwrite entries that were successfully
    extracted; it only fills in *missing* keys.

    Parameters
    ----------
    new_translations:
        Freshly extracted translation dict (will be mutated).
    old_translations:
        The previous contents of ``en.yaml`` as a plain dict, or *None* if
        no previous file existed.
    """
    if not old_translations:
        return

    new_class = new_translations.get("class", {})
    old_class = old_translations.get("class", {})

    if not isinstance(new_class, dict) or not isinstance(old_class, dict):
        log.warning("preserve_existing_sections: unexpected non-dict 'class' section – skipping backfill.")
        return

    for cls, old_cls_data in old_class.items():
        if not isinstance(old_cls_data, dict):
            continue

        for section in ("options", "alarm"):
            old_section = old_cls_data.get(section)
            if not isinstance(old_section, dict):
                continue

            new_class.setdefault(cls, {}).setdefault(section, {})
            for key, value in old_section.items():
                new_class[cls][section].setdefault(key, value)


# ---------------------------------------------------------------------------
# Per-language file update
# ---------------------------------------------------------------------------


def _update_language_file(
    language_file: Path,
    en_translations: dict,
    class_bases: dict[str, list[str]],
    old_en_translations: dict | None,
) -> None:
    """Synchronise a single non-English YAML file with the English source.

    Steps performed:

    1. Migrate any top-level class keys into the ``"class"`` sub-dict.
    2. Prune keys no longer present in English.
    3. Propagate inherited translations within the language (using the same
       topological sort as the English pass).
    4. Add new keys from English, translating ``name_reset`` where a template
       exists for the language.
    5. Save the file if any changes were made.

    Parameters
    ----------
    language_file:
        Path to the language YAML file (e.g. ``translations/de.yaml``).
    en_translations:
        The freshly computed English translations dict.
    class_bases:
        Class inheritance mapping from ``TranslationExtractor``.
    old_en_translations:
        Previous English translations used to detect when an existing
        translation still matches the (now stale) English source and should
        therefore be refreshed.
    """
    language_code = language_file.stem
    log.info("Updating %s…", language_file.name)

    existing: dict = load_yaml(language_file) or {}
    updated = False

    en_class = en_translations.get("class", {})
    en_cli = en_translations.get("cli", {})
    old_en_class = (old_en_translations or {}).get("class", {})
    old_en_cli = (old_en_translations or {}).get("cli", {})

    # 1. Ensure top-level "class" and "cli" sections exist.
    existing.setdefault("class", {})
    if not isinstance(existing.get("cli"), dict):
        existing["cli"] = {}
        updated = True

    # 1b. Migrate stray top-level class keys into "class".
    for k in list(existing.keys()):
        if k in en_class and k not in ("class", "cli"):
            existing["class"].setdefault(k, existing.pop(k))
            updated = True

    # 2. Prune keys absent from English.
    def _prune(d: dict, ref: dict) -> bool:
        """Return True if any key was removed."""
        changed = False
        for k in list(d.keys()):
            if k not in ref:
                log.info("  Removing obsolete key: %s", k)
                del d[k]
                changed = True
            elif isinstance(d[k], dict) and isinstance(ref[k], dict):
                if _prune(d[k], ref[k]):
                    changed = True
        return changed

    if _prune(existing, en_translations):
        updated = True

    prune_empty_dicts(existing)

    # 3. Propagate within the language using topological order.
    def _value_is_english_or_placeholder(cls: str, key: str, subkey: str | None, val: object) -> bool:
        """True if *val* appears to be an untranslated English (or placeholder) string."""
        if isinstance(val, str) and any(p in val for p in _UNRESOLVED_TOKENS):
            return True
        # Compare against current and previous English values.
        en_val = en_class.get(cls, {}).get(key) if subkey is None else en_class.get(cls, {}).get(key, {}).get(subkey)
        old_val = old_en_class.get(cls, {}).get(key) if subkey is None else old_en_class.get(cls, {}).get(key, {}).get(subkey)
        return val == en_val or (old_val is not None and val == old_val)

    for cls in topological_sort(class_bases):
        if cls not in class_bases or cls not in existing["class"]:
            continue
        for base in class_bases[cls]:
            if base not in existing["class"]:
                continue
            base_trans = existing["class"][base]
            for key in ("options", "attributes", "alarm", "name"):
                if key not in base_trans:
                    continue
                base_val = base_trans[key]
                if key not in existing["class"][cls]:
                    existing["class"][cls][key] = base_val.copy() if isinstance(base_val, dict) else base_val
                    updated = True
                elif isinstance(base_val, dict) and isinstance(existing["class"][cls][key], dict):
                    for subkey, subval in base_val.items():
                        cur = existing["class"][cls][key].get(subkey)
                        if cur is None or _value_is_english_or_placeholder(cls, key, subkey, cur):
                            if cur != subval:
                                existing["class"][cls][key][subkey] = subval
                                updated = True
                elif not isinstance(base_val, dict):
                    cur = existing["class"][cls][key]
                    if _value_is_english_or_placeholder(cls, key, None, cur) and cur != base_val:
                        existing["class"][cls][key] = base_val
                        updated = True

    # 4a. Sync class translations.
    for cls, cls_val in en_class.items():
        if cls not in existing["class"]:
            section = cls_val.copy() if isinstance(cls_val, dict) else cls_val
            if isinstance(section, dict) and "name_reset" in section and language_code in RESET_TRANSLATIONS:
                base_name = section.get("name", "")
                if not base_name and isinstance(section["name_reset"], str) and section["name_reset"].startswith("Set "):
                    base_name = section["name_reset"][4:]
                if base_name:
                    section["name_reset"] = RESET_TRANSLATIONS[language_code].format(name=base_name)
            existing["class"][cls] = section
            updated = True
            log.info("  Added new key: %s", cls)
            continue

        if not isinstance(cls_val, dict):
            continue

        for subkey, subval in cls_val.items():
            if subkey not in existing["class"][cls]:
                if subkey == "name_reset" and language_code in RESET_TRANSLATIONS:
                    base_name = existing["class"][cls].get("name", cls_val.get("name", ""))
                    if not base_name and isinstance(subval, str) and subval.startswith("Set "):
                        base_name = subval[4:]
                    existing["class"][cls][subkey] = RESET_TRANSLATIONS[language_code].format(name=base_name) if base_name else subval
                else:
                    existing["class"][cls][subkey] = subval
                updated = True
                log.info("  Added new subkey: %s.%s", cls, subkey)

            elif isinstance(subval, dict):
                for subsubkey, subsubval in subval.items():
                    if subsubkey not in existing["class"][cls][subkey]:
                        existing["class"][cls][subkey][subsubkey] = subsubval
                        updated = True
                        log.info("  Added new subsubkey: %s.%s.%s", cls, subkey, subsubkey)
                    elif existing["class"][cls][subkey][subsubkey] != subsubval:
                        cur = existing["class"][cls][subkey][subsubkey]
                        old_en = old_en_class.get(cls, {}).get(subkey, {}).get(subsubkey)
                        force_update = (old_en is not None and old_en != subsubval) or _value_is_english_or_placeholder(cls, subkey, subsubkey, cur)
                        if force_update:
                            existing["class"][cls][subkey][subsubkey] = subsubval
                            updated = True

            elif existing["class"][cls][subkey] != subval:
                cur = existing["class"][cls][subkey]
                old_en = old_en_class.get(cls, {}).get(subkey)
                force_update = (old_en is not None and old_en != subval) or _value_is_english_or_placeholder(cls, subkey, None, cur)
                if force_update:
                    if subkey == "name_reset" and language_code in RESET_TRANSLATIONS:
                        base_name = existing["class"][cls].get("name", "")
                        if not base_name and isinstance(subval, str) and subval.startswith("Set "):
                            base_name = subval[4:]
                        existing["class"][cls][subkey] = RESET_TRANSLATIONS[language_code].format(name=base_name) if base_name else subval
                    else:
                        existing["class"][cls][subkey] = subval
                    updated = True

    # 4b. Sync CLI translations.
    for key, value in en_cli.items():
        if key not in existing["cli"]:
            existing["cli"][key] = value
            updated = True
            log.info("  Added new CLI key: %s", key)
            continue
        if not isinstance(value, dict):
            continue
        for subkey, subval in value.items():
            if subkey not in existing["cli"][key]:
                existing["cli"][key][subkey] = subval
                updated = True
            elif existing["cli"][key][subkey] != subval:
                old_en = old_en_cli.get(key, {}).get(subkey)
                cur = existing["cli"][key][subkey]
                force_update = (old_en is not None and old_en != subval) or cur == old_en or any(p in str(cur) for p in _UNRESOLVED_TOKENS)
                if force_update:
                    existing["cli"][key][subkey] = subval
                    updated = True

    if updated:
        save_yaml(language_file, existing)
        log.info("  Saved %s", language_file.name)
    else:
        log.info("  No changes needed for %s", language_file.name)


def propagate_to_other_translations(
    en_translations: dict,
    translations_dir: Path,
    class_bases: dict[str, list[str]],
    old_en_translations: dict | None = None,
    *,
    max_workers: int = 4,
) -> None:
    """Update all non-English YAML files in *translations_dir*.

    Files are processed in parallel using a ``ThreadPoolExecutor`` so that
    YAML I/O for multiple languages overlaps.

    Parameters
    ----------
    en_translations:
        Freshly computed English translations.
    translations_dir:
        Directory containing all ``*.yaml`` translation files.
    class_bases:
        Class inheritance mapping from ``TranslationExtractor``.
    old_en_translations:
        Previous English snapshot used for change detection.
    max_workers:
        Maximum number of threads for parallel file I/O.
    """
    language_files = [p for p in translations_dir.glob("*.yaml") if p.name != "en.yaml"]

    def _update(path: Path) -> None:
        _update_language_file(path, en_translations, class_bases, old_en_translations)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_update, lf): lf for lf in language_files}
        for future in as_completed(futures):
            exc = future.exception()
            if exc:
                log.error("Error updating %s: %s", futures[future].name, exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full translation extraction and propagation pipeline.

    1. Parse all ``.py`` files under ``sigenergy2mqtt/`` with
       ``TranslationExtractor``.
    2. Parse ``config/cli.py`` with ``CLIHelpExtractor``.
    3. Merge hard-coded seed translations (alarm sensor labels, Modbus
       register attributes, etc.).
    4. Propagate inherited translations using topological sort.
    5. Write ``translations/en.yaml`` (preserving existing comments).
    6. Synchronise all other language files.
    """
    package_dir = Path(__file__).parent.parent / "sigenergy2mqtt"

    # Seed translations that cannot be extracted via AST.
    sensor_translations: dict = {
        "AlarmSensor": {
            "no_alarm": "No Alarm",
            "unknown_alarm": "Unknown (bit{bit}∈{value})",
        },
        "ReadOnlySensor": {
            "attributes": {
                "source": "Modbus Register {address}",
                "source_range": "Modbus Registers {start}-{end}",
            }
        },
        "WriteOnlySensor": {"name_on": "Power On", "name_off": "Power Off"},
        "MqttOverriddenSensor": {"attributes": {"source": "MQTT Override"}},
    }

    # 1. Extract sensor translations.
    extractor = TranslationExtractor()
    for py_file in package_dir.glob("**/*.py"):
        if py_file.name == "i18n.py" or "test" in py_file.name:
            continue
        try:
            extractor.visit(ast.parse(py_file.read_text(encoding="utf-8")))
        except Exception as exc:
            log.error("Error parsing %s: %s", py_file, exc)

    merge_translations(sensor_translations, extractor.translations)

    # 2. Propagate inheritance.
    propagate_translations(sensor_translations, extractor.class_bases)

    # 3. Extract CLI help.
    config_cli_path = package_dir / "config" / "cli.py"
    cli_translations = extract_cli_help(config_cli_path)
    if cli_translations:
        log.info("Extracted %d CLI help texts.", len(cli_translations))

    # 4. Assemble and sort the full translation dict.
    raw_all = prune_empty_dicts(
        {
            "class": sort_dict(sensor_translations),
            **({"cli": sort_dict(cli_translations)} if cli_translations else {}),
        }
    )
    assert isinstance(raw_all, dict)
    all_translations: dict = sort_dict(raw_all)

    # 5. Load the previous en.yaml (for comment preservation and diff detection).
    en_yaml_path = package_dir / "translations" / "en.yaml"
    old_all_translations: dict | None = None
    all_translations_commented: CommentedMap | None = None

    if en_yaml_path.exists():
        with en_yaml_path.open(encoding="utf-8") as fh:
            all_translations_commented = get_yaml().load(fh)
        if isinstance(all_translations_commented, dict):
            old_all_translations = _strip_comments(all_translations_commented)

    # 6. Backfill safety-net entries and re-sort.
    preserve_existing_sections(all_translations, old_all_translations)
    all_translations = sort_dict(all_translations)

    # 7. Write en.yaml.
    if all_translations_commented is not None:
        deep_update_commented(all_translations_commented, all_translations)
    else:
        all_translations_commented = _to_commented(all_translations)

    save_yaml(en_yaml_path, all_translations_commented)
    log.info("Successfully updated %s (comments preserved).", en_yaml_path)

    # 8. Propagate to other languages.
    propagate_to_other_translations(
        all_translations,
        package_dir / "translations",
        extractor.class_bases,
        old_all_translations,
    )
    log.info("Done!")


if __name__ == "__main__":
    main()
