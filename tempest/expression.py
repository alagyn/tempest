class BaseExpression:
    """
    Base expression class. Expressions evaluate to a single string
    replacement
    """

    def __init__(self):
        pass

    def evaluate(self) -> str:
        raise NotImplementedError()


class ExpressionList(BaseExpression):
    """
    List of expressions that get evaluated in sequence
    """

    def __init__(self):
        self.subExprs: list[BaseExpression] = []

    def addExpr(self, expr: BaseExpression):
        self.subExprs.append(expr)

    def evaluate(self) -> str:
        return "\n".join([x.evaluate() for x in self.subExprs])


class RawTextExpression(BaseExpression):
    """
    Literal text expression
    """

    def __init__(self, text: str):
        self.text = text.replace("\n", "\\n")

    def evaluate(self) -> str:
        return f'f.write("{self.text}")'


class EvalExpression(BaseExpression):
    """
    Python expression to be evaluated and stringified
    """

    def __init__(self, text: str):
        self.text = text

    def evaluate(self) -> str:
        return f'f.write(str({self.text}))'


class CodeExpression(BaseExpression):
    """
    A python conditional statement to be executed and inner expressions
    """

    def __init__(self, code: str, subExprs: ExpressionList):
        self.code = code
        self.subExprs = subExprs

    def evaluate(self) -> str:
        children = self.subExprs.evaluate()
        children = children.replace("\n", "\n    ")
        return self.code + ":\n    " + children
