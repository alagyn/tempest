import unittest

from io import StringIO
import tempest
import logging

BASIC = """
# This is a markdown file

Hello my name is {name=}

My friends are:
{for f in friends:}
    - {f=}

{divisor = 2}
{for i in range(5):}
    {if i % divisor == 0:}
        Did you know {i=} is divisible by {divisor=}

I can even evaluate stuff: {len(name)=}

Small condition {0 if name == "Jimmy" else 1=}
"""

BASIC_EXPECTED = """
# This is a markdown file

Hello my name is Jimmy

My friends are:
- Carl
- Steve
- Greg

Did you know 0 is divisible by 2
Did you know 2 is divisible by 2
Did you know 4 is divisible by 2

I can even evaluate stuff: 5

Small condition 0
"""

WHITESPACE1 = """
{for i in range(2):}
    {if i % 2 == 0:}
        hmm
         {i=}
            {i=}
         {if i == 0:}
            huh
"""

WHITESPACE1_EXP = """
hmm
 0
    0
huh
"""

WIERD_DELIMS = """
<{for i in range(2):)>
    - <{i=)>
"""

WIERD_DELIMS_EXP = """
- 0
- 1
"""

MISSING_CLOSE = "{if x asdf"

EMPTY_EXPR = "asdf {}"
EMPTY_EXPR_EXP = "asdf "


class TestTempest(unittest.TestCase):

    def test_basic(self):

        def basic(template, exp, values, od, cd):
            t = tempest.parse_template_str(template, od, cd)
            out = StringIO()
            t.generate(out, values)
            self.assertEqual(exp, out.getvalue())

        values = {
            "name": "Jimmy",
            "friends": ["Carl", "Steve", "Greg"],
        }

        basic(BASIC, BASIC_EXPECTED, values, '{', '}')
        basic(WHITESPACE1, WHITESPACE1_EXP, {}, '{', '}')
        basic(WIERD_DELIMS, WIERD_DELIMS_EXP, {}, '<{', ")>")
        basic(MISSING_CLOSE, MISSING_CLOSE, {}, "{", '}')
        basic(EMPTY_EXPR, EMPTY_EXPR_EXP, {}, "{", "}")

    def test_syntax_errors(self):

        syntax_errors = [
            "my name is {for x in range(2):}",
            "my other name is {asdf()}",
            "{asdf()} my other name is",
            "{for x in range(2):} my name is",
            "{if asdf:} {x=}",
            "{x=} {if asdf:}",
        ]

        log = logging.getLogger()

        for text in syntax_errors:
            try:
                x = log.getChildren()
                t = tempest.parse_template_str(text, "{", "}")
                self.fail("Exception should have been raised")
            except:
                pass
