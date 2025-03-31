# tempest
Syntax-independent text templating library

Easily embed literal python code into any file.

Features:
- Configurable open/close delimiters
- Works with any language
- It's just more python

# Big Scary Security Warning
This library will execute arbitrary code contained in the template. **Do not allow untrusted templates to be executed.**

## Install

`pip install tempest-fmt`

## Example

### Template
```md
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
```

### Python Implementation
```py
import tempest

t = tempest.parse_template_file("myTemplate.md", "{", "}")

values = {
    "name": "Jimmy",
    "friends": ["Carl", "Steve", "Greg"],
}

with open("output.md", mode='w') as f:
    t.generate(f, value)
```

### Output file
```md
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
```

## Syntax specifics

**For simplicity, we will assume the delimiters to be `{ }`**  
All python statements will be contained within the delimiters, 
any text outside will be considered raw text.

Statements of the form `{<expr>=}` will be evaluated as `str(<expr>)` and directly inserted into the text.  
All other statements will be considered logical statements. Such statements **must** follow indentation rules for python and should have no raw text on the line. Any statements following will have indentation stripped, this includes raw text (extra whitespace after the expected indentation is left as-is).

**Indentation is important**  
*Leading spaces replaced with dots for this example*

```md
{for x in range(3):}
....- {x}

My next thing
```
Will produce
```md
- 0
- 1
- 2

My next thing
```

Compared to
```md
{for x in range(3):}
....- {x}
....

My next thing
```
Will produce
```md
- 0

- 1

- 2

My next thing
```

