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
@v_args(inline=True)
class ODataFilterTransformer(Transformer):
    def and_expr(self, left, right):
        return {"and": [left, right]}

    def or_expr(self, left, right):
        return {"or": [left, right]}

    def not_expr(self, expr):
        return {"not": expr}

    def comparison_expr(self, field, op, value):
        return {"a": field, "op": str(op), "b": value}

    def function_call(self, name, args=None):
        return {"function": str(name), "args": args if args else []}

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
        return value  # just pass through the transformed path