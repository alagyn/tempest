import re
from typing import TextIO

from tempest.template import Template
from tempest import expression as expr

# TODO Need to figure out how to handle whitespace around expressions better?


class _Parser:

    def __init__(self, template_file: str, open_delim: str, close_delim: str):
        with open(template_file, mode='r') as f:
            # This does not strip ending newlines
            self.text = f.readlines()

        self.len = len(self.text)
        self.od = open_delim
        self.cd = close_delim
        self.idx = 0
        self.depth = 0
        self.indentSize: int = 0

    def parse(self) -> Template:
        out = self._recurseParse()
        return Template(out)

    def _recurseParse(self) -> expr.ExpressionList:
        out = expr.ExpressionList()

        curRawText = []
        error = False

        for lineIdx, line in enumerate(self.text):
            # count indents
            numIndents = 0
            firstCharIsOpen = False
            if self.depth > 0:
                if self.indentSize == 0:
                    if self.depth != 1:
                        raise RuntimeError("Well, this shouldn't happen")
                    # count the whitespace
                    indent = 0
                    for x in line:
                        if x == " ":
                            indent += 1
                        else:
                            break
                    if indent != 0:
                        # Don't set it if the line was empty/not indented
                        self.indentSize = indent
                        numIndents = 1
                else:
                    for i in range(min(self.indentSize * self.depth,
                                       len(line))):
                        if line[i] != " ":
                            numIndents = i // self.indentSize
                            if i % self.indentSize != 0:
                                print(
                                    f"Warning, indentation is not consistent at line {lineIdx}, treating it as if indented {numIndents} time(s)"
                                )
                            break
                        if numIndents == 0:
                            # if we got here, then we consumed the correct amount of whitespace
                            numIndents = self.depth

            textStart = numIndents * self.indentSize
            firstCharIsOpen = line.startswith(self.od, textStart)

            # handle unindents
            if len(line.strip()) > 0 and self.depth != numIndents:
                # go ahead and clear the current raw text if the indent changes
                out.addExpr(
                    expr.RawTextExpression("".join(curRawText), self.depth))
                curRawText.clear()
                self.depth = numIndents

            exprStart = line.find(self.od)
            if exprStart < 0:
                # No expressions, consume the line and continue
                curRawText.append(line[textStart:])
                continue

            exprTextStart = exprStart + len(self.od)
            # We found an open delim, try to find the end
            exprEnd = line.find(self.cd, exprTextStart)
            if exprEnd < 0:
                # TODO better logging?
                print(
                    f"Warning, no closing delimiter for open at line {lineIdx + 1}:{exprStart}"
                )
                # Treat this as raw text
                curRawText.append(line[textStart:])
                continue

            # We found an expression, check what type it is
            exprText = line[exprTextStart:exprEnd]
            if exprText[-1] == ":" or exprText[-1] != "=":
                # we have a block or a statement
                if not firstCharIsOpen:
                    # TODO different error if inconsistent whitespace
                    print(
                        f"Error, line {lineIdx + 1}: lines containing statements must only contain the statement and whitespace, '{line.strip()}'"
                    )
                    error = True
                    # pretend this is valid and just ignore the start of the line
                if exprText[-1] == ":":
                    self.depth += 1
                # first, take any preceeding text lines and make a raw text expression
                if len(curRawText) > 0:
                    out.addExpr(
                        expr.RawTextExpression("".join(curRawText),
                                               numIndents))
                    curRawText.clear()
                # then make the code expression
                out.addExpr(expr.CodeExpression(exprText, numIndents))
            else:
                # we have an expression to turn into a string

                # first get preceeding text for the line
                curRawText.append(line[textStart:exprStart])
                out.addExpr(
                    expr.RawTextExpression("".join(curRawText), numIndents))
                curRawText.clear()

                # then strip pull out the expression
                if exprTextStart == exprEnd:
                    print(
                        f"Warning, empty expression at line {lineIdx + 1}:{exprStart}"
                    )
                else:
                    out.addExpr(
                        expr.EvalExpression(line[exprTextStart:exprEnd - 1],
                                            numIndents))

                # get remaining text for the line
                curRawText.append(line[exprEnd + len(self.cd):])

            # end for line

        if len(curRawText) > 0:
            out.addExpr(expr.RawTextExpression("".join(curRawText),
                                               self.depth))

        if error:
            raise RuntimeError("Parse Failed")

        return out


def parse_template(template_file: str, open_delim: str,
                   close_delim: str) -> Template:

    p = _Parser(template_file, open_delim, close_delim)
    return p.parse()
