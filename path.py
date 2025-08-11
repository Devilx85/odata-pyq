
from lark import Lark, Transformer, v_args
# Full grammar for OData $filter with complex types


odata_path_grammar = r"""
start: resource_path

resource_path: "/" segment ("/" segment)* "/"?
segment: dotted_name key_predicate?
key_predicate: "(" key_values ")"
key_values: key_value ("," key_value)* | value ("," value)*

key_value: dotted_name "=" value
value: SIGNED_NUMBER      -> number
     | ESCAPED_STRING     -> string

dotted_name: /[a-zA-Z_][a-zA-Z0-9_.]*/

%import common.SIGNED_NUMBER
%import common.ESCAPED_STRING
%import common.WS
%ignore WS
"""



@v_args(inline=True)
class ODataPathTransformer(Transformer):
    def dotted_name(self, token):
        return str(token)

    def key_value(self, key, val):
        return (str(key), val)

    def key_values(self, *args):
        if all(isinstance(arg, tuple) for arg in args):
            return dict(args)  # named keys
        else:
            return list(args)  # positional keys



    def key_predicate(self, keys):
        if isinstance(keys, dict) or isinstance(keys, list):
            return keys
        return [keys]


    def segment(self, name, keys=None):
        return {"entity": str(name), "keys": keys}

    def number(self, token):
        return int(token)

    def string(self, token):
        return str(token)[1:-1]

    def resource_path(self, *segments):
        return list(segments)

    def start(self,path):
        return path