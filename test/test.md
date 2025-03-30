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