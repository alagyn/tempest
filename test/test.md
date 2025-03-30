This is my file

{if a == b:}
    {should = True}
    I should

    Maybe
{else:}
    {should = False}
    I shouldn't
{if should:}
    {for x in myValues:}
        My value is {x=}
