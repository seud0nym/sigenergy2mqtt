import ast
import inspect
from pathlib import Path

from sigenergy2mqtt.config import config, const


def test_reload_handles_all_env_constants():
    """
    Ensures that every constant defined in sigenergy2mqtt.config.const
    that starts with SIGENERGY2MQTT_ is explicitly handled in the
    Config.reload method's match statement.
    """
    # 1. Get all constants that should be handled
    expected_constants = set()
    for name in dir(const):
        if name.startswith("SIGENERGY2MQTT_") and name != "SIGENERGY2MQTT_CONFIG":
            expected_constants.add(name)

    # 2. Parse Config.reload to find handled constants
    # We use AST to avoid executing code and to ensure we find explicit usage
    config_file = Path(inspect.getfile(config.Config))
    tree = ast.parse(config_file.read_text())

    handled_constants = set()

    class CaseVisitor(ast.NodeVisitor):
        def visit_Match(self, node):
            # We are looking for the match block in Config.reload
            # But the visitor visits all nodes.
            # So we just collect all attribute accesses that look like const.SOME_NAME
            # inside match cases.
            # Logic:
            # - Visit all 'cases' in the match
            # - For each case, look at the pattern
            # - If pattern is MatchValue(value=Attribute(...)), extract it
            # - If pattern is MatchOr(patterns=[...]), recurse
            for case in node.cases:
                self.visit_pattern(case.pattern)

        def visit_pattern(self, node):
            if isinstance(node, ast.MatchValue):
                self.extract_const(node.value)
            elif isinstance(node, ast.MatchOr):
                for p in node.patterns:
                    self.visit_pattern(p)
            # Python < 3.10 might parse differently, but we assume 3.10+ for 'match'

        def extract_const(self, node):
            # Check if it is const.SIGENERGY2MQTT_...
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "const":
                handled_constants.add(node.attr)

    # Find the Reload method body
    reload_method_node = None
    for node in tree.body:  # Module body
        if isinstance(node, ast.ClassDef) and node.name == "Config":
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name == "reload":
                    reload_method_node = method
                    break

    assert reload_method_node is not None, "Could not find Config.reload method"

    # Visit the reload method to find the match statement
    visitor = CaseVisitor()
    visitor.visit(reload_method_node)

    # 3. Compare
    missing = expected_constants - handled_constants

    # IGNORED: Some constants might be intentionally handled implicitly or aggregated.
    # Adjust this set if there are exceptions, but the goal is to be explicit.
    # const.SIGENERGY2MQTT_CONFIG is usually base config, often not in the main loop or handled differently.
    # We excluded it above.

    # Also exclude constants that are handled in 'handled above' block or other special logic if any.
    # Looking at the code:
    # case (
    #     const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY
    #     | const.SIGENERGY2MQTT_MODBUS_AUTO_DISCOVERY_PING_TIMEOUT
    #     | ...
    # ):
    #     pass
    # These are handled in the AST visitor (it handles MatchOr), so they should be in 'handled_constants'.

    assert not missing, f"The following constants in const.py are not handled in Config.reload: {missing}"
