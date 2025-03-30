import re
from typing import TextIO

from tempest.template import Template
from tempest import expression as expr

# TODO Need to figure out how to handle whitespace around expressions better?


class _Parser:

    def __init__(self, template_file: str, open_delim: str, close_delim: str):
        with open(template_file, mode='r') as f:
            self.text = f.read()

        self.len = len(self.text)
        self.od = open_delim
        self.cd = close_delim
        self.idx = 0
        self.depth = 0

    def parse(self) -> Template:
        out = self._recurseParse()
        if self.depth > 0:
            raise RuntimeError(f"Missing {self.depth} closing delimiter(s)")
        return Template(out)

    def _recurseParse(self) -> expr.ExpressionList:
        out = expr.ExpressionList()
        while self.idx < self.len:
            nextExpr = self.text.find(self.od, self.idx)
            nextCloseExpr = self.text.find(self.cd, self.idx)

            if nextExpr != -1 and nextExpr < nextCloseExpr:
                if self.idx != nextExpr:
                    # Consume all the text up to the next expr
                    out.addExpr(
                        expr.RawTextExpression(self.text[self.idx:nextExpr]))
                self.idx = nextExpr + len(self.od)
                self.depth += 1

                # TODO disallow weird newlines in expressions

                nextCloseExpr = self.text.find(self.cd, self.idx)
                if nextCloseExpr == self.idx:
                    # TODO make this better
                    print("Warning, empty expression")
                elif self.text.startswith(self.od, self.idx):
                    # Double open delims indicates a block with conditions
                    # followed by an expression list
                    # read the expression
                    self.idx += len(self.od)
                    code = self.text[self.idx:nextCloseExpr]
                    self.idx = nextCloseExpr + len(self.cd)
                    # now recursively parse the sub expressions
                    subExpr = self._recurseParse()
                    out.addExpr(expr.CodeExpression(code, subExpr))
                else:
                    # otherwise it's a py expression to be evaluated
                    out.addExpr(
                        expr.EvalExpression(self.text[self.idx:nextCloseExpr]))
                    self.idx = nextCloseExpr + len(self.cd)
                    # we hit the close, so dec the depth
                    self.depth -= 1

            elif nextCloseExpr != -1:
                # End of the current expression
                # consume text and exit
                if self.idx != nextCloseExpr:
                    out.addExpr(
                        expr.RawTextExpression(
                            self.text[self.idx:nextCloseExpr]))
                if self.depth == 0:
                    # TODO maybe just make this a warning...
                    raise RuntimeError(
                        "Invalid closing delimiter, no open delimiter")
                self.depth -= 1
                # consume close delim
                self.idx = nextCloseExpr + len(self.cd)
                break
            else:
                # everything else is text
                out.addExpr(expr.RawTextExpression(self.text[self.idx:]))
                self.idx = len(self.text)
                break

        return out


def parse_template(template_file: str, open_delim: str,
                   close_delim: str) -> Template:

    p = _Parser(template_file, open_delim, close_delim)
    return p.parse()
