"""
SYNCRA Declarative AST Compiler & Dependency DAG Engine
Evaluates calculation rules via structured JSON Abstract Syntax Trees (AST).
Strictly operates with Decimal fixed-point arithmetic (zero binary float usage).
Detects circular dependencies via topological sort.
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, ROUND_UP
from typing import Dict, Any, List, Set, Optional
from .diagnostic_errors import (
    SyncraException,
    SyncraGateValidationException,
    SyncraMissingConfigurationException
)


class RoundingPolicy:
    HALF_UP = "HALF_UP"
    DOWN = "DOWN"
    UP = "UP"

    @classmethod
    def apply(cls, value: Decimal, precision: int = 2, policy: str = "HALF_UP") -> Decimal:
        exp = Decimal("10") ** (-precision)
        if policy == cls.HALF_UP:
            return value.quantize(exp, rounding=ROUND_HALF_UP)
        elif policy == cls.DOWN:
            return value.quantize(exp, rounding=ROUND_DOWN)
        elif policy == cls.UP:
            return value.quantize(exp, rounding=ROUND_UP)
        else:
            raise SyncraMissingConfigurationException(
                code="SYNCRA_ERR_INVALID_ROUNDING_POLICY",
                message=f"Unknown rounding policy: {policy}"
            )


class AstEngine:
    ALLOWED_OPERATORS = {
        "ADD",
        "SUBTRACT",
        "MULTIPLY",
        "DIVIDE",
        "PRORATA",
        "MIN",
        "MAX"
    }

    @classmethod
    def evaluate_node(cls, node: Dict[str, Any], context: Dict[str, Decimal]) -> Decimal:
        """Evaluates an AST node recursively."""
        node_type = node.get("type")

        if node_type == "CONSTANT":
            val = node.get("value")
            if val is None:
                raise SyncraException("AST_INVALID_CONSTANT", "Constant node missing value")
            return Decimal(str(val))

        if node_type == "VARIABLE":
            var_name = node.get("name")
            if not var_name or var_name not in context:
                raise SyncraException(
                    "AST_VARIABLE_NOT_FOUND",
                    f"Variable '{var_name}' not provided in evaluation context."
                )
            return context[var_name]

        if node_type == "EXPRESSION":
            op = node.get("operator")
            if op not in cls.ALLOWED_OPERATORS:
                raise SyncraException(
                    "AST_OPERATOR_NOT_ALLOWED",
                    f"Operator '{op}' is not in approved operators list."
                )

            left = cls.evaluate_node(node["left"], context)
            right = cls.evaluate_node(node["right"], context)

            if op == "ADD":
                return left + right
            elif op == "SUBTRACT":
                return left - right
            elif op == "MULTIPLY":
                return left * right
            elif op == "DIVIDE":
                if right == Decimal("0"):
                    raise SyncraException("AST_DIVISION_BY_ZERO", "Division by zero in AST expression.")
                return left / right
            elif op == "PRORATA":
                # (left * right) / base_denominator (e.g., worked_days / 30)
                base = Decimal(str(node.get("base", "30")))
                return (left * right) / base
            elif op == "MIN":
                return min(left, right)
            elif op == "MAX":
                return max(left, right)

        raise SyncraException("AST_UNKNOWN_NODE_TYPE", f"Unknown AST node type: {node_type}")

    @classmethod
    def execute_rule(
        cls,
        rule_spec: Dict[str, Any],
        context: Dict[str, Decimal],
        enforce_gate1: bool = True
    ) -> Decimal:
        """
        Executes a candidate rule AST with Gate 1 validation and rounding policy enforcement.
        """
        if enforce_gate1:
            if not rule_spec.get("implementation_autorisee", False):
                raise SyncraGateValidationException(
                    code="SYNCRA_ERR_UNAUTHORIZED_RULE_EXECUTION",
                    message=f"Rule '{rule_spec.get('code')}' has implementation_autorisee=False. Execution blocked.",
                    details={"code": rule_spec.get("code"), "status": rule_spec.get("status")}
                )

        rounding_config = rule_spec.get("rounding")
        if not rounding_config or "policy" not in rounding_config or "precision" not in rounding_config:
            raise SyncraMissingConfigurationException(
                code="SYNCRA_ERR_ROUNDING_POLICY_MISSING",
                message=f"Rule '{rule_spec.get('code')}' lacks mandatory rounding policy specification."
            )

        raw_result = cls.evaluate_node(rule_spec["expression_tree"], context)
        return RoundingPolicy.apply(
            raw_result,
            precision=rounding_config["precision"],
            policy=rounding_config["policy"]
        )


class DependencyGraph:
    """Manages rule dependency DAG and detects circular loops."""
    def __init__(self):
        self.dependencies: Dict[str, Set[str]] = {}

    def add_dependency(self, rule_code: str, depends_on: str):
        if rule_code == depends_on:
            raise SyncraException(
                "SYNCRA_ERR_SELF_DEPENDENCY",
                f"Rule '{rule_code}' cannot depend on itself."
            )
        if rule_code not in self.dependencies:
            self.dependencies[rule_code] = set()
        self.dependencies[rule_code].add(depends_on)

    def get_execution_order(self) -> List[str]:
        """
        Topological sort of rules.
        Detects circular dependencies and raises explicit error.
        """
        all_nodes = set(self.dependencies.keys())
        for deps in self.dependencies.values():
            all_nodes.update(deps)

        in_degree = {node: 0 for node in all_nodes}
        graph: Dict[str, List[str]] = {node: [] for node in all_nodes}

        for node, deps in self.dependencies.items():
            for dep in deps:
                graph[dep].append(node)
                in_degree[node] += 1

        queue = [n for n, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for neighbor in graph[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(all_nodes):
            raise SyncraException(
                code="SYNCRA_ERR_CIRCULAR_DEPENDENCY",
                message="Circular dependency detected in calculation rule graph.",
                details={"unresolved_nodes": list(all_nodes - set(order))}
            )

        return order


# Aliases
SyncraAstEngine = AstEngine
SyncraRoundingPolicy = RoundingPolicy
