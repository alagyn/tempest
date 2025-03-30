from typing import TextIO, Any

from tempest.expression import BaseExpression


class Template:

    def __init__(self, expr: BaseExpression):
        self.code = expr.evaluate()

    def generate(self, output: TextIO, values: dict[str, Any]):
        v = values.copy()
        v["f"] = output
        exec(self.code, locals=v)
