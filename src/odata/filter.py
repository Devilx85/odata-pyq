import ast
from lark import Lark, Transformer, v_args

# Class allows to strucutre correctly $filter expression returning back
# a tree of dictionaries with logical and comparision expressions

# Full grammar for OData $filter with complex types
odata_filter_grammar = r"""
    ?start: expr


    ?expr: or_expr

    ?or_expr: and_expr
            | or_expr "or" and_expr   -> or_expr

    ?and_expr: not_expr
            | and_expr "and" not_expr -> and_expr

    ?not_expr: "not" atom             -> not_expr
            | atom


    ?atom: comparison
         | function_call
         | field
         | value
         | "(" expr ")"

    ?comparison: atom operator atom   -> comparison_expr

    function_call: FUNC_NAME "(" [args] ")"
    field: path
    path: NAME ("/" NAME)*

    OPERATOR: "eq" | "ne" | "gt" | "lt" | "ge" | "le"
    operator: OPERATOR

    value: SIGNED_NUMBER      -> number
         | ESCAPED_STRING     -> string  
         | SINGLE_QUOTED_STRING -> string
         | "true"             -> true
         | "false"            -> false
         | "null"            -> null

    
    SINGLE_QUOTED_STRING: /'(?:[^']|'')*'/


    FUNC_NAME.2: "startswith" | "endswith" | "contains" | "substringof"
               | "length" | "indexof" | "tolower" | "toupper" | "trim"
               | "concat" | "year" | "month" | "day" | "hour" | "minute" | "second"
                   
    args: expr ("," expr)*

    NAME: /[a-zA-Z_][a-zA-Z0-9_]*/

    %import common.SIGNED_NUMBER
    %import common.ESCAPED_STRING
    %import common.WS
    %ignore WS
"""
class ODataPrimitve:
    def __init__(self,value):
        self.value = value

class ODataFunction:
    def __init__(self,name,args):
        self.name = name
        self.args = args

class ODataField:
    def __init__(self,name):
        self.name = name

class ODataOperator:
    def __init__(self,name,a,b):
        self.name = name
        self.a = a
        self.b = b
class ODataLogOperator:
    def __init__(self,name,left,right):
        self.name = name
        self.right = right
        self.left = left
@v_args(inline=True)
class ODataFilterTransformer(Transformer):
    def and_expr(self, left, right):
        return ODataLogOperator("and",left,right)

    def or_expr(self, left, right):
        return ODataLogOperator("or",left,right)

    def not_expr(self, expr):
        return  ODataLogOperator("not",None,expr)

    def comparison_expr(self, field, op, value):
        return ODataOperator(str(op),field,value)

    def function_call(self, name, args=None):
        args = args if args else []
        return ODataFunction( str(name),args)

    def args(self, *expressions):
        return list(expressions)

    def operator(self, token):
        return str(token)

    def number(self, token):
        return ODataPrimitve(float(token))

    def string(self, token):
        text = str(token)
        if text.startswith('"'):
            return ODataPrimitve(ast.literal_eval(text))  # handles \" correctly
        elif text.startswith("'"):
            # Remove outer quotes and replace doubled single quotes with one
            return ODataPrimitve(text[1:-1].replace("''", "'"))


    def true(self):
        return ODataPrimitve(True)

    def false(self):
        return ODataPrimitve(False)
    def null(self):
        return ODataPrimitve(None)
    
    def path(self, *parts):
        return "/".join(str(p) for p in parts)

    def field(self, value):
        return ODataField(value)  # just pass through the transformed path