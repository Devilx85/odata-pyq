from lark import Lark, Transformer, v_args

odata_orderby_grammar = r"""
    ?start: orderby_list

    orderby_list: orderby_item ("," orderby_item)*

    orderby_item: path direction?   -> orderby_entry

    DIRECTION: "asc" | "desc"
    direction: DIRECTION

    path: CNAME ("/" CNAME)*

    %import common.CNAME
    %import common.WS
    %ignore WS
"""


class ODataOrderByTransformer(Transformer):

    def orderby_entry(self, items):
        field = items[0]
        direction = items[1] if len(items) > 1 else "asc"
        return {str(field): str(direction)}

    def path(self, items):
        return "/".join(str(p) for p in items)

    def direction(self, items):
        return str(items[0])

    def orderby_list(self, items):
        result = {}
        for item in items:
            result.update(item)
        return result
