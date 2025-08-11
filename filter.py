from lark import Lark, Transformer, v_args

# Class allows to strucutre correctly $filter expression returning back
# a tree of dictionaries with logical and comparision expressions

# Full grammar for OData $filter with complex types
odata_filter_grammar = r"""
    ?start: expr

    ?expr: and_expr
         | or_expr  
         | not_expr
         | atom

    and_expr: atom "and" expr
    or_expr: atom "or" expr  
    not_expr: "not" atom

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

    SINGLE_QUOTED_STRING: /'[^']*'/

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

@v_args(inline=True)
class ODataFilterTransformer(Transformer):
    def and_expr(self, left, right):
        return {"and": [left, right]}

    def or_expr(self, left, right):
        return {"or": [left, right]}

    def not_expr(self, expr):
        return {"not": expr}

    def comparison_expr(self, field, op, value):
        return {"field": field, "op": str(op), "value": value}

    def function_call(self, name, args=None):
        return {"function": str(name), "args": args if args else []}

    def args(self, *expressions):
        return list(expressions)

    def operator(self, token):
        return str(token)

    def number(self, token):
        return float(token)

    def string(self, token):
        return str(token)[1:-1]  # remove quotes

    def true(self, _):
        return True

    def false(self, _):
        return False

    def path(self, *parts):
        return "/".join(str(p) for p in parts)

    def field(self, value):
        return value  # just pass through the transformed path