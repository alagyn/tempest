from typing import TextIO, Any
from io import StringIO
import logging

log = logging.getLogger("tempest")


class _BaseExpression:
    """
    Base expression class. Expressions evaluate to a single string
    replacement
    """

    def __init__(self, indent: int, lineNum: int):
        self.indent = indent
        self.lineNum = lineNum

    def evaluate(self) -> str:
        raise NotImplementedError()


class _RawTextExpression(_BaseExpression):
    """
    Literal text expression
    """

    def __init__(self, text: str, indent: int, lineNum: int):
        super().__init__(indent, lineNum)
        self.text = text
        self.text = self.text.replace("\\", "\\\\")
        self.text = self.text.replace("\n", "\\n")
        self.text = self.text.replace("\"", "\\\"")

    def evaluate(self) -> str:
        return "    " * self.indent + f'_f.write("{self.text}") # line {self.lineNum}'


class _EvalExpression(_BaseExpression):
    """
    Python expression to be evaluated and stringified
    """

    def __init__(self, text: str, indent: int, lineNum: int):
        super().__init__(indent, lineNum)
        self.text = text

    def evaluate(self) -> str:
        return "    " * self.indent + f'_f.write(str({self.text})) # line {self.lineNum}'


class _CodeExpression(_BaseExpression):
    """
    A python conditional statement to be executed and inner expressions
    """

    def __init__(self, code: str, indent: int, lineNum: int):
        super().__init__(indent, lineNum)
        self.code = code

    def evaluate(self) -> str:
        return "    " * self.indent + self.code + f' # line {self.lineNum}'


class Template:

    def __init__(self, exprs: list[_BaseExpression]):
        lines = [expr.evaluate() for expr in exprs]
        codeText = "\n".join(lines)
        self.code = compile(codeText, "<string>", mode="exec")

    def generate(self, output: TextIO, values: dict[str, Any]):
        v = values.copy()
        v["_f"] = output
        exec(self.code, locals=v)


class _Parser:

    def __init__(self, template: TextIO, open_delim: str, close_delim: str):
        # This does not strip ending newlines
        self.text = template.readlines()

        self.len = len(self.text)
        self.od = open_delim
        self.cd = close_delim
        self.idx = 0
        self.depth = 0
        self.indentSize: int = 0

    def parse(self) -> Template:
        out: list[_BaseExpression] = []
        error = False

        overrideTextStart = -1
        for lineIdx, line in enumerate(self.text):
            lineNum = lineIdx + 1
            # count indents
            numIndents = 0
            firstCharIsOpen = False
            if self.depth > 0:
                if self.indentSize == 0:
                    assert self.depth == 1
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
                    for idx in range(
                            min(self.indentSize * self.depth, len(line))):
                        c = line[idx]
                        if c != " ":
                            numIndents = idx // self.indentSize
                            if idx % self.indentSize != 0:
                                log.warning(
                                    f"Indentation is not consistent at line {lineNum}, treating it as if indented {numIndents} time(s), '{line.strip()}'"
                                )
                            break
                        if numIndents == 0:
                            # if we got here, then we consumed the correct amount of whitespace
                            numIndents = self.depth

            textStart = numIndents * self.indentSize
            firstCharIsOpen = line.startswith(self.od, textStart)

            # handle unindents
            if self.depth != numIndents:
                self.depth = numIndents

            expressions: list[tuple[int, int]] = []
            idx = 0
            while True:
                exprStart = line.find(self.od, idx)
                if exprStart < 0:
                    break
                exprEnd = line.find(self.cd, exprStart + len(self.od))
                if exprEnd < 0:
                    # just add as is, will get handled in the for loop below
                    expressions.append((exprStart, exprEnd))
                    break
                idx = exprEnd + len(self.cd)
                expressions.append((exprStart, exprEnd))

            if len(expressions) == 0:
                # No expressions, consume the line and continue
                out.append(
                    _RawTextExpression(line[textStart:], numIndents, lineNum))
                continue

            for exprIdx, (exprStart, exprEnd) in enumerate(expressions):
                exprTextStart = exprStart + len(self.od)
                # We found an open delim, try to find the end
                exprEnd = line.find(self.cd, exprTextStart)
                if exprEnd < 0:
                    log.warning(
                        f"No closing delimiter for open at line {lineNum}:{exprStart}, '{line.strip()}'"
                    )
                    # Treat this as raw text
                    out.append(
                        _RawTextExpression(line[textStart:], numIndents,
                                           lineNum))
                    continue

                # We found an expression, check what type it is
                exprText = line[exprTextStart:exprEnd].strip()

                if len(exprText) > 0 and (exprText[-1] == ":"
                                          or exprText[-1] != "="):
                    # we have a block or a statement
                    if len(expressions) > 1:
                        log.error(
                            f"Line {lineNum}: lines can only contain one statement, '{line.strip()}'"
                        )
                        error = True
                        # pretend we can accept this, following statements will just be ignored
                    if not firstCharIsOpen:
                        foundText = False
                        for x in line[:exprStart]:
                            if x != " ":
                                foundText = True
                                log.error(
                                    f"Line {lineNum}: lines containing statements must only contain the statement and whitespace, '{line.strip()}'"
                                )
                                error = True
                                # pretend this is valid and just ignore the start of the line
                        if not foundText:
                            log.warning(
                                f"Line {lineNum}: Extra whitespace detected, check your indentation, '{line.strip()}'"
                            )

                    # make the code expression
                    out.append(_CodeExpression(exprText, self.depth, lineNum))
                    # inc depth if block
                    if exprText[-1] == ":":
                        self.depth += 1
                    break
                else:
                    # we have an expression to turn into a string

                    # if we are the first expression
                    if exprIdx == 0:
                        # get any text leading up to it
                        out.append(
                            _RawTextExpression(line[textStart:exprStart],
                                               self.depth, lineNum))

                    # then strip pull out the expression
                    if len(exprText) > 0:
                        out.append(
                            _EvalExpression(exprText[:-1], self.depth,
                                            lineNum))
                    else:
                        log.warning(
                            f"Warning, empty expression at line {lineNum}:{exprStart}, '{line.strip()}'"
                        )
                        # just ignore it, it will get stripped

                    # if we have another expressoin
                    if exprIdx < len(expressions) - 1:
                        # get the text in between expressions
                        splitTextEnd = expressions[exprIdx + 1][0]
                        out.append(
                            _RawTextExpression(
                                line[exprEnd + len(self.cd):splitTextEnd],
                                self.depth, lineNum))
                    else:
                        # get remaining text for the line
                        out.append(
                            _RawTextExpression(line[exprEnd + len(self.cd):],
                                               self.depth, lineNum))
                # end for expression
            # end for line

        if error:
            raise RuntimeError("Parse Failed")

        return Template(out)


def parse_template(template: TextIO, open_delim: str,
                   close_delim: str) -> Template:

    p = _Parser(template, open_delim, close_delim)
    return p.parse()


def parse_template_file(template: str, open_delim: str, close_delim: str):
    with open(template, mode='r') as f:
        return parse_template(f, open_delim, close_delim)


def parse_template_str(template: str, open_delim: str, close_delim: str):
    f = StringIO(template)
    return parse_template(f, open_delim, close_delim)
