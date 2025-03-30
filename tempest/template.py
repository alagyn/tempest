from typing import TextIO, Any

from tempest.expression import BaseExpression


class Template:

    def __init__(self, expr: BaseExpression):
        codeText = expr.evaluate()
        self.code = compile(codeText, "<string>", mode="exec")

    def generate(self, output: TextIO, values: dict[str, Any]):
        v = values.copy()
        v["f"] = output
        exec(self.code, locals=v)
