"""Every place the code names another module resolves to something that exists.

Moving or renaming a module breaks references that no test may exercise: an import inside a
function, a data migration, a ``mock.patch`` string, a dotted path in the settings. Python only
finds them when that line runs, so this test reads all of them up front.
"""

import ast
import importlib
import itertools
import pkgutil
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase
from django.utils.module_loading import import_string

ROOT = Path(__file__).resolve().parents[2]
FIRST_PARTY = tuple(sorted(
    path.name for path in ROOT.iterdir()
    if path.is_dir() and (path / '__init__.py').exists() and not path.name.startswith('.')
))
SKIP_DIRS = {'.venv', '.venv-ci', '__pycache__', 'static', 'staticfiles', 'media', 'node_modules'}


def source_files():
    for path in sorted(ROOT.rglob('*.py')):
        if not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            yield path


def module_name(path):
    parts = list(path.relative_to(ROOT).with_suffix('').parts)
    is_package = parts[-1] == '__init__'
    return (parts[:-1] if is_package else parts), is_package


def absolute_module(path, node):
    """The module an ``import from`` statement names, with relative imports resolved."""
    if node.level == 0:
        return node.module
    parts, is_package = module_name(path)
    base = parts if is_package else parts[:-1]
    base = base[:len(base) - (node.level - 1)]
    return '.'.join(base + ([node.module] if node.module else []))


def exists(module, name):
    try:
        imported = importlib.import_module(module)
    except Exception as exc:  # noqa: BLE001 - any failure to import is the finding
        return f'cannot import {module}: {type(exc).__name__}: {exc}'
    if name == '*' or hasattr(imported, name):
        return None
    try:
        importlib.import_module(f'{module}.{name}')
        return None
    except Exception:  # noqa: BLE001
        return f'{module} has no {name!r}'


class LoopValues(ast.NodeVisitor):
    """Finds each ``patch(...)`` call with the literal loops around it, so an f-string target can be expanded."""

    def __init__(self):
        self.loops = []
        self.calls = []

    def visit_For(self, node):
        values = None
        if isinstance(node.iter, (ast.Tuple, ast.List)) and all(isinstance(e, ast.Constant) for e in node.iter.elts):
            values = [e.value for e in node.iter.elts]
        names = [node.target.id] if isinstance(node.target, ast.Name) else []
        self.loops.append({name: values for name in names} if values is not None else {})
        self.generic_visit(node)
        self.loops.pop()

    def visit_Call(self, node):
        func = node.func
        # mock.patch(...) or a bare patch(...) imported from unittest.mock; not client.patch(...), an HTTP PATCH.
        is_mock_patch = (isinstance(func, ast.Name) and func.id == 'patch') or (
            isinstance(func, ast.Attribute) and func.attr == 'patch'
            and isinstance(func.value, (ast.Name, ast.Attribute))
            and ast.unparse(func.value) in ('mock', 'unittest.mock')
        )
        if is_mock_patch and node.args:
            self.calls.append((node, {k: v for frame in self.loops for k, v in frame.items()}))
        self.generic_visit(node)


def patch_targets(tree):
    """(line, target or None) for each patch call. None means the target is built at run time."""
    visitor = LoopValues()
    visitor.visit(tree)
    for call, loop_values in visitor.calls:
        arg = call.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            yield call.lineno, arg.value
        elif isinstance(arg, ast.JoinedStr):
            pieces, names = [], []
            for part in arg.values:
                if isinstance(part, ast.Constant):
                    pieces.append(part.value)
                elif isinstance(part, ast.FormattedValue) and isinstance(part.value, ast.Name) \
                        and loop_values.get(part.value.id):
                    pieces.append(part.value.id)
                    names.append(part.value.id)
                else:
                    pieces = None
                    break
            first = arg.values[0].value if arg.values and isinstance(arg.values[0], ast.Constant) else ''
            if not isinstance(first, str) or first.split('.')[0] not in FIRST_PARTY:
                continue  # not a dotted path into this code base (for example a URL)
            if pieces is None:
                yield call.lineno, None
                continue
            for combo in itertools.product(*(loop_values[n] for n in names)):
                values = dict(zip(names, combo))
                yield call.lineno, ''.join(values.get(p, p) if p in names else p for p in pieces)


def check_target(target):
    module_path, _, attribute = target.rpartition('.')
    try:
        owner = pkgutil.resolve_name(module_path)
    except Exception as exc:  # noqa: BLE001
        return f'patch target {target!r}: {type(exc).__name__}: {exc}'
    return None if hasattr(owner, attribute) else f'patch target {target!r}: {module_path} has no {attribute!r}'


class ReferencesResolveTests(SimpleTestCase):
    def test_every_first_party_import_resolves(self):
        problems = []
        for path in source_files():
            tree = ast.parse(path.read_text())
            where = path.relative_to(ROOT)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = absolute_module(path, node)
                    if module and module.split('.')[0] in FIRST_PARTY:
                        for alias in node.names:
                            found = exists(module, alias.name)
                            if found:
                                problems.append(f'{where}:{node.lineno} {found}')
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split('.')[0] in FIRST_PARTY:
                            try:
                                importlib.import_module(alias.name)
                            except Exception as exc:  # noqa: BLE001
                                problems.append(f'{where}:{node.lineno} cannot import {alias.name}: {exc}')
        self.assertEqual(problems, [], '\n' + '\n'.join(problems))

    def test_every_patch_target_resolves(self):
        problems = []
        for path in source_files():
            if 'tests' not in path.relative_to(ROOT).parts:
                continue
            where = path.relative_to(ROOT)
            for line, target in patch_targets(ast.parse(path.read_text())):
                if target is None:
                    problems.append(
                        f'{where}:{line} patch target is built at run time; write the dotted path out '
                        'or loop over literal values so it can be checked'
                    )
                elif target.split('.')[0] in FIRST_PARTY:
                    found = check_target(target)
                    if found:
                        problems.append(f'{where}:{line} {found}')
        self.assertEqual(problems, [], '\n' + '\n'.join(problems))

    def test_dotted_paths_in_the_settings_resolve(self):
        problems = []

        def walk(value, key):
            if isinstance(value, str):
                if value.split('.')[0] in FIRST_PARTY and value.replace('.', '').replace('_', '').isalnum() \
                        and '.' in value:
                    try:
                        if key.endswith('_MODEL'):
                            apps.get_model(value)  # "app_label.ModelName"
                        else:
                            try:
                                import_string(value)  # a class or function
                            except ImportError:
                                importlib.import_module(value)  # a module, such as SESSION_ENGINE
                    except Exception as exc:  # noqa: BLE001
                        problems.append(f'settings.{key}: {value}: {exc}')
            elif isinstance(value, (list, tuple, set)):
                for item in value:
                    walk(item, key)
            elif isinstance(value, dict):
                for item in value.values():
                    walk(item, key)

        for key in dir(settings):
            if key.isupper():
                walk(getattr(settings, key), key)
        self.assertEqual(problems, [], '\n' + '\n'.join(problems))
