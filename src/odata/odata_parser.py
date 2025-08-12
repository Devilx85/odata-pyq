
import re
from typing import Deque, Dict, List, Any, Optional, Union, Callable, Tuple, Set
from urllib.parse import urlparse, parse_qs,unquote
from lark import Lark
from  odata.path import ODataPathTransformer , odata_path_grammar
from  odata.filter import ODataFilterTransformer , odata_filter_grammar
from  odata.orderby import ODataOrderByTransformer, odata_orderby_grammar

# These OData parser classes allow to parse correctly OData url + queries, both regex and lark are used to correctly form a strucutre of the request

class ODataURLParser:
    def parse_odata_query(query_string):
        """
        Parse OData query strings that contain parameters with nested parentheses and ampersands.
        
        Args:
            query_string (str): The query string to parse (with or without leading ?)
            
        Returns:
            dict: Dictionary with parameter names as keys and lists of values
        """
        # Remove leading ? if present
        if query_string.startswith('?'):
            query_string = query_string[1:]
        
        # URL decode the string first
        decoded = unquote(query_string)
        
        # Split on & but ignore & inside parentheses
        params = ODataURLParser.smart_split(decoded,'&')
        
        result = {}
        for param in params:
            if '=' in param:
                key, value = param.split('=', 1)  # Split only on first =
                if key in result:
                    result[key].append(value)
                else:
                    result[key] = [value]
            else:
                # Parameter without value
                result[param] = ['']
        
        return result


    def smart_split(text,splitter):
        """
        Split a string by ampersands (&), but ignore ampersands inside parentheses or quotes.
        
        Args:
            text (str): The string to split
            
        Returns:
            list: List of split parts with whitespace stripped
        """
        result = []
        current_part = ""
        paren_depth = 0
        in_single_quote = False
        in_double_quote = False
        i = 0
        
        while i < len(text):
            char = text[i]
            
            # Handle escape sequences in quotes
            if (in_single_quote or in_double_quote) and char == '\\' and i + 1 < len(text):
                current_part += char + text[i + 1]
                i += 2
                continue
            
            # Handle quote toggling
            if char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                current_part += char
            elif char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                current_part += char
            # Handle parentheses (only when not in quotes)
            elif char == '(' and not (in_single_quote or in_double_quote):
                paren_depth += 1
                current_part += char
            elif char == ')' and not (in_single_quote or in_double_quote):
                paren_depth -= 1
                current_part += char
            # Handle ampersand splitting
            elif char == splitter and paren_depth == 0 and not (in_single_quote or in_double_quote):
                # We found an ampersand outside of parentheses and quotes
                if current_part.strip():
                    result.append(current_part.strip())
                current_part = ""
            else:
                current_part += char
            
            i += 1
        
        # Add the last part
        if current_part.strip():
            result.append(current_part.strip())
        
        return result


    def parse_expand_parameter(expand_value):
        """
        Parse the $expand parameter value to extract individual expand clauses.
        
        Args:
            expand_value (str): The $expand parameter value
            
        Returns:
            list: List of individual expand clauses
        """
        return ODataURLParser.smart_split(expand_value,',')

    def parse_multiple_entities(s: str):
            """
            Parse a comma-separated list of entities with optional query parameters.
            Returns a list of (entity, params) tuples.
            """
            if not s:
                return []
            
            s = s.strip().strip('/')
            entities = []
            
            # Split by commas, but we need to be careful about commas inside parentheses
            parts = ODataURLParser.smart_split(s,',')
            
            for part in parts:
                part = part.strip()
                if part:
                    entity, params = ODataURLParser.extract_single_entity(part)
                    if entity:
                        entities.append((entity, params))
            
            return entities

    def extract_single_entity(s: str):
        """
        Extract entity name and parameters from a single entity string.
        """
        paren_pos = s.find('(')
        
        if paren_pos == -1:
            # No parentheses
            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", s):
                return s, None
            return s, None
        
        entity = s[:paren_pos]
        
        # Validate entity name
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", entity):
            return None, None
        
        # Extract content between parentheses
        if s.endswith(')'):
            content = s[paren_pos+1:-1]
            return entity, content
        
        return None, None

    def extract_expand_multi(s: str):

        entities = ODataURLParser.parse_multiple_entities(s)
        
        if not entities:
            return None, None
        
        # Return first entity (maintaining compatibility)
        return entities[0]

    # Alternative: return all entities
    def extract_all_entities(s: str):
        """
        Returns all entities as a dictionary.
        """
        entities = ODataURLParser.parse_multiple_entities(s)
        return {entity: params for entity, params in entities}

    def extract_expand(s: str):
        # Handle multiple entities by taking the first one
        entities = ODataURLParser.parse_multiple_entities(s)
        if entities:
            return entities[0]  # Returns (entity, params) tuple
        return None, None

class ODataParser:
    # Parsed values:
    # $filter – Filters results based on a Boolean condition.
    # $select – Specifies which properties to include in the response.
    # $expand – Includes related entities inline with the response.
    # $orderby – Sorts the results by one or more properties.
    # $top – Limits the number of results returned.
    # $skip – Skips a specified number of results.
    # $count – Requests a count of the matching entities.
    # $search – Performs a full-text search (if supported).
    # $format – Specifies the media type of the response (e.g., JSON).
    # $compute – Adds computed properties to the result.
    # $apply – Enables server-side data transformations (e.g., groupby, aggregate).
     
    
    def __init__(self,url:str):
        self.url = url
        
        # Parse the URL
        self.parsed_url = urlparse(url)
        # Get the path
        self.path = self.parsed_url.path
        # Get the query parameters as a dictionary
        self.params = ODataURLParser.parse_odata_query(self.parsed_url.query)

        self.filter = None
        self.select = None
        self.expand = None
        self.orderby = None
        self.top = None
        self.skip = None
        self.count = None
        self.search = None
        self.format = None
        self.skip_token = None
        #self.compute = None
        #self.apply = None
        self.parsed_path = None
    

    def has_parameters(self) -> bool:
        if self.filter or self.select or self.orderby or self.top or self.skip or self.count or self.search:
            return True
        return False
    def run(self):


        if "$count" in self.params:
            if self.params["$count"][0] == "true":
                self.count = True
            else:
                self.count = False
        if "$top" in self.params:
            try:
                self.top = int(self.params["$top"][0])
            except:
                pass
        if "$skip" in self.params:
            try:
                self.skip = int(self.params["$skip"][0])
            except:
                pass
        if "$skiptoken" in self.params:
            try:
                self.skip_token = int(self.params["$skiptoken"][0])
            except:
                pass
        if "$expand" in self.params:
            self.expand = []

            exp_segments = ODataURLParser.smart_split(self.params["$expand"][0],',')
            for seg in exp_segments:

                field , nested = ODataURLParser.extract_expand(seg)

                self.expand.append((field , nested ))

        if "$select" in self.params:
            self.select = self.params["$select"][0].split(',')

        if "$search" in self.params:
            self.search = self.params["$search"][0]

        if "$format" in self.params:
            self.format = self.params["$format"][0]

        #complex  parsing
        if "$filter" in self.params:
            parser_filter = Lark(odata_filter_grammar, parser='lalr', transformer=ODataFilterTransformer())
            self.filter = parser_filter.parse(self.params["$filter"][0])
            #print(self.filter)

        if "$orderby" in self.params:
            parser_orderby = Lark(odata_orderby_grammar, parser='lalr', transformer=ODataOrderByTransformer())
            self.orderby = parser_orderby.parse(self.params["$orderby"][0])

        parser_path = Lark(odata_path_grammar, parser='lalr', transformer=ODataPathTransformer())
        self.parsed_path = parser_path.parse(self.path)


