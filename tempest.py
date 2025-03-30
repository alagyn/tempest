from typing import TextIO, Any


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
        codeText = "\n".join([expr.evaluate() for expr in exprs])
        try:
            self.code = compile(codeText, "<string>", mode="exec")
        except Exception as err:
            raise

    def generate(self, output: TextIO, values: dict[str, Any]):
        v = values.copy()
        v["_f"] = output
        exec(self.code, locals=v)


class _Parser:

    def __init__(self, template_file: str, open_delim: str, close_delim: str):
        with open(template_file, mode='r') as f:
            # This does not strip ending newlines
            self.text = f.readlines()

        self.filename = template_file
        self.len = len(self.text)
        self.od = open_delim
        self.cd = close_delim
        self.idx = 0
        self.depth = 0
        self.indentSize: int = 0

    def parse(self) -> Template:
        out: list[_BaseExpression] = []
        error = False

        for lineIdx, line in enumerate(self.text):
            lineNum = lineIdx + 1
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
                                    f"Warning, indentation is not consistent at line {lineNum}, treating it as if indented {numIndents} time(s), '{line.strip()}'"
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
                    print(
                        f"Warning, no closing delimiter for open at line {lineNum}:{exprStart}, '{line.strip()}'"
                    )
                    # TODO
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
                    # TODO better logging?
                    print(
                        f"Warning, no closing delimiter for open at line {lineNum}:{exprStart}, '{line.strip()}'"
                    )
                    # Treat this as raw text
                    out.append(
                        _RawTextExpression(line[textStart:], numIndents,
                                           lineNum))
                    continue

                # We found an expression, check what type it is
                exprText = line[exprTextStart:exprEnd].strip()
                if exprText[-1] == ":" or exprText[-1] != "=":
                    # we have a block or a statement
                    if not firstCharIsOpen:
                        # TODO different error if inconsistent whitespace
                        print(
                            f"Error, line {lineNum}: lines containing statements must only contain the statement and whitespace, '{line.strip()}'"
                        )
                        error = True
                        # pretend this is valid and just ignore the start of the line
                    if len(expressions) > 1:
                        print(
                            f"Error, line {lineNum}: lines can only contain one statement, '{line.strip()}'"
                        )
                        error = True
                        # pretend we can accept this, following statements will just be ignored
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
                    if exprTextStart == exprEnd:
                        print(
                            f"Warning, empty expression at line {lineNum}:{exprStart}, '{line.strip()}'"
                        )
                    else:
                        out.append(
                            _EvalExpression(line[exprTextStart:exprEnd - 1],
                                            self.depth, lineNum))

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


def parse_template(template_file: str, open_delim: str,
                   close_delim: str) -> Template:

    p = _Parser(template_file, open_delim, close_delim)
    return p.parse()
