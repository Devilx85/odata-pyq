
from enum import Enum
from functools import reduce
from operator import and_
from typing import List, Tuple
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse
from peewee import Model,ForeignKeyField,Field
from .odata_parser import ODataParser
from logging import Logger

class DataType(Enum):
    """Enumeration representing different types of OData elements in the system.

    Attributes:
        ENTITY (int): Represents a single entity or record (value = 1)
        COLLECTION (int): Represents a collection of entities (value = 2)
        FIELD (int): Represents a field or attribute of an entity (value = 3)
    """
    ENTITY = 1
    COLLECTION = 2
    FIELD = 3

class NavigationPath:
    def __init__(self,cl_model,path="",data_type=DataType.COLLECTION):
        self.cl_model = cl_model
        self.where = []
        self.data_type = data_type
        self.path = path
        self.full_path = path
        self.via_backref = False
        self.backref_field = None
        self.id = None
        

    def add_id_cond(self,keys:List[str]):
        """Function adds id = key where condition for peewee instance 

        Args:
            keys (int): ID keys (currently class supports only a single key -> keys[0])
        """
        #Curreently supporting only 1 ID key
        if keys:
            self.where.append( self.cl_model.id == keys[0] )
            self.data_type = DataType.ENTITY
            self.id = keys[0]
    def join_backref(self,field1,field2):
        """Function adds field = key where condition for peewee instance, for the backrefs 

        Args:
            field1 - peewee field
            field2 - peewee field
        """
        self.backref_field = field1
        self.where.append( field1 == field2)


class PeeweeODataQuery:
    """Main class for OData operations

    Currently supports basic queries:
        GET             operations with: $select, $filter, $orderby, $skip , $top, $expand (can hanle nested parameters)
                        for filter operations logical operations(AND/OR) and basic comparision operations are implemneted (+contains,startswith,endswith)
        CREATE          no deep sctructure support
        UPDATE/PATCH    no deep sctructure support
        DELETE          

        Relatioship orerations or functions are not yet implemented

    """
    def __init__(self,models:list, url:str , expandable=[],logger:Logger = None,etag_callable=None,select_always=["id"]):
        """Constructor

        Args:
            models:             allowed models
            url:                url to parse
            expandable          allowed peewee model clases to expand, but not to browse as root (no modification allowed)
            logger              logger to log operations
            etag_callable       object function to get etag (all models should have it implemented if given)
            select_always       a list of fileds to select alwys like id or modification date/time, since they are needed for some specific manipulation before final output
        """
        self.models=models
        self.navigated_class = None
        self.logger = logger
        self.etag_callable = etag_callable

        #Parse Parameters
        self.url = url
        self.parser = ODataParser(url)
        self.parser.run()

        self.parent = None
        self.select = []
        self.select_fields = []
        self.joins = []
        self.where_cond = []
        self.path_classes = None
        self.expands = []
        self.sorts = []
        self.select_always = select_always

        # Add a cache for model relationships
        self._model_rel_cache = {}
        self.expandable = expandable

        #Forced pagination
        self.skiptoken_size = 0
        self.skiptoken_page = 0
        self.next_page = 0

        #Hidden fields
        self.hidden = []

        #Expand complex
        self.expand_complex = True

        #Search fiedls
        self.search_fields = []

        #model related restrictions
        self.restrictions = {}

        self.apply_navigation_model()

    def set_expand_complex(self,expand:bool):
        """Method to determine if to expand complex (foregin keys) fields by default (not backrefs!)

        Args:
            size            number of records to produce
        """        
        self.expand_complex = expand
    def set_skiptoken(self,size:int):
        """Method to set forced pagination size

        Args:
            size            number of records to produce
        """        
        self.skiptoken_size = size
    def set_hidden_fields(self,fields=List[str]):
        """Method to set fileds to be hidden in results (without output too consumer)

        Args:
            fields        list of fields
        """
        self.hidden  = fields
    def set_search_fields(self,model_fields=List[str]):
        """Method to set model fileds' names to search a string in with $search parameter

        Args:
            fields        list of field names
        """
        self.search_fields  = model_fields
    def write_log(self,message:str):
        """Method to write logs if logger is provided

        Args:
            message        message string
        """
        if self.logger:
            self.logger.info(message)
    
    def _include_search_fieds(self,model,search:str):
        """To be run right before request to add search  fields with AND operator
        ([collected where conditions]) AND ([search fields contain $search])

        Args:
            model       Peewee model
            search      search string
        """  
        if not self.search_fields or search == None or search == "":
            self.write_log(f"No fields to search, skipping")
            return
            
        search_conds = []
        for field in self.search_fields:
            if field in model._meta.fields:
                search_conds.append(getattr(model,field).contains(search))
                self.write_log(f"Adding search in {model} {field} with {search}")

        if search_conds:
            base_cond = reduce(and_, self.where_cond) if self.where_cond else None
            # Combine search conditions
            search_cond = reduce(and_, search_conds)

            # Merge both with AND
            if base_cond:
                final_cond = base_cond & search_cond
            else:
                final_cond = search_cond

            self.where_cond = [final_cond]

    def add_restricition(self,model,where_conds=[]):
        """ Adds restrictive "where" conditions for the model

        Args:
            model           model class for restricitions
            where_conds     list of peewee "where" conditions
        """             
        self.restrictions[model.__name__] = where_conds

    def query(self,where=[],join=[]):
        """ Execute Query (GET)

        Args:
            where     list of peewee conditions to apply for the model
            join      list of joins to apply to the model

            these are used for expand recusrive function processing
        """      

        #Apply implemented query options
        #   
        self.apply_filter_model()
        self.apply_expand_model(starting_class=self.navigated_class)
        self.apply_sorting_model()
        self.apply_select_model()
        select =  [self.navigated_class]
        backrefs =  []

        #Apply select fields if exist
        if self.select_fields:
            for mod_class,field in self.select_fields:
                select.append(field)
            self.write_log(f"Selecting fields {self.select}")


        self.write_log(f"Building req ...sel {self.select} join {self.joins} where {self.where_cond} , backrefs {backrefs}")

        #Collect all joins and conds 
        for item in self.path_classes[:-1]:
            self.where_cond.extend(item.where)
            self.joins.append(item.cl_model)


        self.where_cond.extend(self.path_classes[-1].where) 

        self.where_cond.extend(where)
        if self.navigated_class.__name__ in self.restrictions:
            self.where_cond.extend(self.restrictions[self.navigated_class.__name__])

        self.joins.extend(join)
        
        self.write_log(f"Query : sel {self.navigated_class} {select} join {self.joins} where {self.where_cond} with fetch {backrefs}")
        
        #Support for auto expanding FK definitions in the model
        if self.expand_complex:
            for field_name, field_object in self.navigated_class._meta.fields.items():
                if isinstance(field_object, ForeignKeyField) and hasattr(field_object,'rel_model'):
                    if field_object.rel_model not in select:
                        select.append(field_object.rel_model)
                    if field_object.rel_model not in self.joins:
                        self.joins.append(field_object.rel_model)

        query = self.navigated_class.select(*select)

        if self.joins:
            query = query.join(*self.joins)
        
        #Add search conditions if exist
        self._include_search_fieds(self.navigated_class,self.parser.search)

        if self.where_cond:
            query = query.where(*self.where_cond)
        if self.sorts:    
            query = query.order_by(*self.sorts)
        
        if self.skiptoken_size != 0:
            cnt_query = query
            total = cnt_query.count()
            if total > self.skiptoken_size:
                if self.parser.skip_token == None:
                    self.parser.skip_token = 0
                self.parser.skip = self.parser.skip_token * self.skiptoken_size
                
                if self.parser.skip > total or ( self.parser.skip  + self.skiptoken_size) >= total:
                    self.next_page = -1 
                else:
                    self.next_page = self.parser.skip_token + 1

                self.parser.top  =  self.skiptoken_size
                
                self.write_log(f"Skipping {self.parser.skip} records and limit to {self.parser.top} with skiptoken = {self.parser.skip_token}")
                
        if self.parser.skip is not None:
            query = query.offset(self.parser.skip)
        if self.parser.top is not None:
            query = query.limit(self.parser.top)

        if self.parser.count == True:
            query = query.count()




        return query
    def create(self,data={},rewrite_filed_values={},default_field_values={}):  
        """ Create entity (POST)

        Args:
            data                      dict of values for creation
            rewrite_filed_values      dict of fields to overwrite
            default_field_values      dict of default values

        """       
        #Query params cannot be applied to mutations
        if self.parser.has_parameters():
            raise Exception(f"Mutation does not support query parameters!")
        
        cur_navig = self.path_classes[-1]

        if cur_navig.cl_model not in self.models:
            raise Exception(f"Data collection is not supported") 
        
        if cur_navig.data_type != DataType.COLLECTION:
            raise Exception(f"Can only create entities for collections!")

        #Checking backref
        if len(self.path_classes)>1 and self.path_classes[-2].data_type == DataType.ENTITY:
            prev_navig = self.path_classes[-2]
            self.write_log(f"Setting backref : {cur_navig.backref_field.name} to {prev_navig.id} ")
            data[cur_navig.backref_field.name] = prev_navig.id


        #update data to rewrite fields
        data.update(rewrite_filed_values)

        # Add default fields only if missing
        for key, value in default_field_values.items():
            if key not in data:
                data[key] = value

        created_entry = self.navigated_class.create(**data)

        return created_entry
    def update(self,data={},where=[],rewrite_filed_values={},default_field_values={},patch=False):   
        """ Update entity (PUT/PATCH)

        Args:
            data                      dict of values for creation
            where                     add "where" restriction e.g (User.id = 'user123')
            rewrite_filed_values      dict of fields to overwrite
            default_field_values      dict of default values
            patch                     Patching or full replace?

        """        
        if self.parser.has_parameters():
            raise Exception(f"Mutation does not support query parameters!")
        
        cur_navig = self.path_classes[-1]
        
        if cur_navig.cl_model not in self.models:
            raise Exception(f"Data collection is not supported") 
    
        if cur_navig.data_type != DataType.ENTITY:
            raise Exception(f"Can only update entities ,not collections!")
        
        #First execute a query to get udpated record
        res_data = list(self.query(where=where))

        if not res_data:
            raise Exception(f"Entiity does not exist")
        if len(res_data) != 1:
            raise Exception(f"Selection returned back more than one entity!")    
        
        entity = res_data[0]
        
        if len(self.path_classes)>1 and self.path_classes[-2].data_type == DataType.ENTITY:
            prev_navig = self.path_classes[-2]
            self.write_log(f"Setting backref : {cur_navig.backref_field.name} to {prev_navig.id} ")
            data[cur_navig.backref_field.name] = prev_navig.id
        


        #update data to rewrite fields
        data.update(rewrite_filed_values)

        # Add default fields only if missing
        for key, value in default_field_values.items():
            if key not in data:
                data[key] = value

        #loop provided fields
        for field_name, field_obj in entity._meta.fields.items():
                if field_obj.primary_key :
                    continue
                if field_name not in data:
                    if patch == False:
                        raise Exception("Field {field_name} was not provided, use patch to modify specific fields!")
                    else:
                        continue 
                setattr(entity, field_name,data[field_name])
        

        entity.save()

        return entity

    def delete(self, where=[]): 
        """ Delete entity (PUT/PATCH)

        Args:
            where   "where" restricition conditions for deleteion
        """         
        if self.parser.has_parameters():
            raise Exception(f"Mutation does not support query parameters!")
        
        cur_navig = self.path_classes[-1]
        
        if cur_navig.cl_model not in self.models:
            raise Exception(f"Data collection is not supported") 
    
        if cur_navig.data_type != DataType.ENTITY:
            raise Exception(f"Can only update entities ,not collections!")
        
        res_data = list(self.query(where=where))

        if not res_data:
            raise Exception(f"Entiity does not exist")
        if len(res_data) != 1:
            raise Exception(f"Selection returned back more than one entity!")    
        
        entity = res_data[0]

        entity.delete_instance()

        return entity
    
    def _expression_to_string(self,expr):
        """ Peewee expression to string

        Args:
            expr   Peewee expression

        """   
        try:
            lhs = getattr(expr.lhs, 'name', str(expr.lhs))
            op = expr.op.name if hasattr(expr.op, 'name') else str(expr.op)
            rhs = repr(expr.rhs)
            return f"{lhs} {op} {rhs}"
        except Exception as e:
            return f"<Error parsing expression: {e}>"
           

    def get_field_name_from_backref(self,referred_model:Model, backref_name:str)-> Tuple[Field,Model]:
        """ Gets the relevant Field and Model for the backref of the provided Model

        Args:
            referred_model    model to search in
            backref_name      Backref name


        """   
        for model, fields in referred_model._meta.model_refs.items():
            for field in fields:
                if field.backref == backref_name:
                    return field,model
        return None,None


    def _resolve_field(self,data:str):
        """ Resolves field names (eg order/date)

        Args:
            data    field name in relation to currently processed navigated class

        """   
        self.write_log("Resolving name {data}")

        cur_class = self.navigated_class
        cache_key = (cur_class, data)
         # Use cached relationships if available
        if data in self._model_rel_cache:
            res_cl,res_dt,_ = self._model_rel_cache[cache_key]
            if res_dt != DataType.FIELD:
                raise Exception(f"Referenced fieled is Entity or collection, not a field {data}")
            return res_cl
        
        fld = data
        
        data_type = DataType.ENTITY

        #Logic for subfields and backrefs
        if '/' in data:
            segs = data.split('/')
            fld = segs[-1]
            for seg in segs[:-1]:
                rel_class , data_type , backref= self.find_model_rel(cur_class,seg)
                if not rel_class:
                    self.write_log(f"No name {seg}")
                    raise Exception(f"Unknown field {seg}") 
                
                #allow only defined models
                if rel_class not in self.models and rel_class not in self.expandable:
                    raise Exception("Path or attribute does not exist")
                
                self.write_log(f"Resolved class for the field ref {rel_class}")
                cur_class = rel_class

                #add class to the collection
                #if rel_class not in self.select:
                #    self.select.append(rel_class)

                if rel_class not in self.joins:
                    self.joins.append(rel_class)
                

        if data_type == DataType.COLLECTION and backref==False:
            raise Exception(f"Relation was resolved instead of entity for field {seg}") 
        
        if fld not in cur_class._meta.fields:
           raise Exception(f"Cannot find field {fld} in object {cur_class}") 

        field = getattr(cur_class,fld)
        
        # Cache the resolved field
        cache_key = (cur_class, data)
        self._model_rel_cache[cache_key] = (field,DataType.FIELD,False)

        return field
    
    def _resolve_value(self,data):
        return data
    
    def _filter_run_expression(self,expression):
        """ Resolves OData expression recieved from parser (see Odata parser)

        Args:
            expression    OData expressiion

        """ 
        #get first logical expression
        fk = next(iter(expression)) 
        if fk == "and" or fk == "or" or fk == "not":
            return self._filter_apply_expressions(fk,expression[fk])

        # Use a dictionary to map operators to their corresponding functions
        operator_map = {
            "eq": lambda f, v: f == v,
            "ne": lambda f, v: f != v,
            "gt": lambda f, v: f > v,
            "lt": lambda f, v: f < v,
            "ge": lambda f, v: f >= v,
            "le": lambda f, v: f <= v,
        }

        function_map = {
            "contains": lambda a1, a2: a1.contains(a2),
            "startswith": lambda a1, a2: a1.startswith(a2),
            "endswith": lambda a1, a2: a1.endswith(a2),
        }
        
        #function or comparison?
        if fk == "field":
           
            field = self._resolve_field(expression["field"])
            value = self._resolve_value(expression["value"])
            op = expression["op"]     

            
            if op in operator_map:
                self.write_log(f"Applying operator: {op}")
                return operator_map[op](field, value)
            
        elif fk == "function":
            func = expression["function"]
            args = expression["args"]
            self.write_log(f"Applying function: { func }")
            if len(args) != 2:
                raise Exception(f"Function param error {func}") 
            arg1 = self._resolve_field(args[0]) 
            arg2 = self._resolve_value(args[1])   

            if func in function_map:
                return function_map[func](arg1, arg2)      
               
        raise Exception(f"Unknown expression {expression} ")   
    
    def _filter_apply_expressions(self,log_operator,expressions:List[dict]):
        """ Applies expresions for the logical operators AND and OR

        Args:
            expression    OData expressiion

        """ 
        self.write_log(f"Applying filter expression { log_operator } for {expressions}")

        if log_operator  == "not":
            left_expr = expressions
            left_expr_res = self._filter_run_expression(left_expr)
        else:
            left_expr = expressions[0]
            left_expr_res = self._filter_run_expression(left_expr)            
            right_expr = expressions[1]
            right_expr_res = self._filter_run_expression(right_expr)

        if log_operator == "and":
            return (left_expr_res & right_expr_res)
        elif log_operator == "or":
            return (left_expr_res | right_expr_res)
        elif log_operator == "not":
            return ~(left_expr_res)
        raise Exception(f"Unknown logical operator {log_operator}")

    def apply_select_model(self):
        """ Applies $select parameter

        Args:
            

        """ 
        if self.parser.select: 
            total_sel = []
            total_sel.extend(self.parser.select)
            total_sel.extend(self.select_always)

            for field in total_sel:
                
                if field in self.navigated_class._meta.fields and field not in self.select_fields:
                    self.write_log(f"Adding selection field {field}")
                    self.select_fields.append((self.navigated_class,getattr(self.navigated_class,field)))

    def apply_sorting_model(self):
        """ Applies $orderby parameter

        Args:
            

        """ 
        if self.parser.orderby:
            self.write_log(f"Applying sorting  { self.parser.orderby }")
            for field_name, direction in self.parser.orderby.items():
                field = self._resolve_field(field_name)
                self.sorts.append(field.desc() if direction == 'desc' else field.asc())

    def apply_filter_model(self):
        """ Applies $filter parameter

        Args:
            

        """ 
        odata_filter = self.parser.filter
        self.write_log(f"Applying filter {self.parser.filter}")
        if odata_filter:
            fk = next(iter(odata_filter))
            expr = None
            if fk == "and" or fk == "or":
                expr = self._filter_apply_expressions(fk,odata_filter[fk])
            else:
                expr = self._filter_run_expression(odata_filter)
            self.where_cond.append(expr)



    def apply_navigation_model(self):
        """ Applies navigation path 

        Args:
            

        """ 
        start_seg = self.parser.parsed_path[0]["entity"]

        ini_class = next((item for item in self.models if item.__name__.lower()+"s" == start_seg ),None)

        if not ini_class:
            raise Exception(f"Object collection {start_seg} does not exist or not defined") 

        self.path_classes = []
        self.navigated_class = ini_class
        ini_path = NavigationPath(ini_class,path=start_seg)
    
        if self.parser.parsed_path[0]["keys"]:
            ini_path.add_id_cond(self.parser.parsed_path[0]["keys"])

        self.path_classes.append(ini_path)


        for item in self.parser.parsed_path[1:]:

            ref_class = None
            #discover foreignkey or backref
            found_class, data_type, backref = self.find_model_rel(self.navigated_class,item["entity"])
            
            self.write_log(f"Searching path: { item['entity'] }")
            if found_class != None:
                if self.path_classes[-1].data_type == DataType.COLLECTION and data_type == DataType.COLLECTION:
                    raise Exception(f"Incorrect path , two collections cannot be realted {self.path_classes[-1].path} and {item['entity']}")
                
                self.write_log(f"Checking if class {found_class} is allowed in {self.allowed_objects} ")

                if found_class not in self.models and found_class not in self.expandable:
                    raise Exception(f"Operations is not allowed!")
                
                self.write_log(f"Found path: { item['entity'] }")
                
                pclass = next((item.cl_model for item in self.path_classes if item.cl_model == found_class ),None)

                #avoid circular referencing
                if pclass != None:
                    raise Exception(f"Circular relation was discoverd in path {self.parser.path} , involving {self.navigated_class}")
                
                #Add navigation path to the collection
                ref_class = NavigationPath(found_class,path=item["entity"],data_type=data_type)

                ref_class.via_backref = backref

                if backref:
                    #for the backref add related key and id in the navigation
                    connected_field , _= self.get_field_name_from_backref(found_class,item["entity"])
                    ref_class.join_backref(connected_field,self.path_classes[-1].cl_model.id)
                
                # if key provided in the Odata path apply it
                if "keys" in item and item["keys"]:
                    self.write_log(f"Adding keys: { item['keys'] }")
                    ref_class.add_id_cond(item["keys"])
                    data_type = DataType.ENTITY

            else:
                raise Exception(f"Odata path cannot be found {item['entity']}")
            
            self.path_classes.append(ref_class)
            self.navigated_class = found_class

            for item in self.path_classes:
                self.write_log(f"Dicsovering path...{item.cl_model} {item.where} ")
            

    def apply_expand_model(self,starting_class:Model):
        """ Applies $expand to a model

        Args:
            starting_class    model class to loop for backrefs and foreignkeys to check

        """ 
        if self.parser.expand != None:
            for item,nested in self.parser.expand:
                exp_class, data_type,backref = self.find_model_rel(starting_class,item)
                if exp_class:

                    if exp_class not in self.models and exp_class not in self.expandable:
                        raise Exception(f"Operation (expand) is not allowed!")
                    if item not in self.expands:
                        self.write_log(f"Adding expand {item} {nested}")
                        #add expand parameter for later processing
                        self.expands.append((exp_class,item,nested))
                else:
                    raise Exception(f"Cannot expand unknown item {item}")
    def find_model_rel(self,model_class,name:str) -> Tuple[object , DataType,bool]:
        """ Discovers realtionship via field name (fks and backrefs)

        Args:
            model_class    peewee model
            name           field name

        """ 
        cache_key = (model_class, name)
        if cache_key in self._model_rel_cache:
            self.write_log(f"Resolved relation via cache: { name } from { model_class } value {self._model_rel_cache[cache_key]}")
            return self._model_rel_cache[cache_key]
        
        # Detect foreign key fields
        for field_name, field_object in model_class._meta.fields.items():
            if field_name == name and isinstance(field_object, ForeignKeyField):
                self._model_rel_cache[cache_key] = (field_object.rel_model,DataType.FIELD,False)
                self.write_log(f"Resolved relation via model field: { name } from { model_class }")
                return self._model_rel_cache[cache_key] 


        # Detect backrefs by checking for ReverseRelationDescriptor type name

        if hasattr(model_class,name):
            attr = getattr(model_class, name)
            self.write_log(f"Listing backref: { name } from { type(attr).__name__  }")
            if type(attr).__name__ == 'BackrefAccessor':
                related_model = getattr(attr, 'rel_model', None)
                self._model_rel_cache[cache_key] = (related_model,DataType.COLLECTION,True)
                self.write_log(f"Resolved relation via model backref: { name } from { model_class }")
                return self._model_rel_cache[cache_key]

        self.write_log(f"Cannot find: { name } from { model_class }")
        self._model_rel_cache[cache_key] = (None,None,None)

        return  None , None , None

    
    def _extract_before_parenthesis(self,text):
        """ Extracts path without id data

        Args:
            text  string

        """ 
        return text.split('(')[0].strip()

    def _replace_skiptoken(self,new_token: str) -> str:
        """ Replaces skiptoken in url

        Args:
            new_token    new pagination token

        """ 
        # Parse the URL into components
        parsed_url = urlparse(self.url)
        
        # Parse the query string into a dictionary
        query_params = parse_qs(parsed_url.query, keep_blank_values=True)
        
        # Replace or add the $skiptoken parameter
        query_params['$skiptoken'] = [new_token]
        
        # Reconstruct the query string
        new_query = urlencode(query_params, doseq=True, quote_via=quote)



        # Rebuild the full URL
        updated_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        
        return updated_url

        

    def peewee_result_to_dict_or_list(self, query_result,with_odata_id=True,include_etag=False)-> list | dict:
        """ Converts query result to a dictionary or list od dicts

        Args:
            query_result    model class to loop for backrefs and foreignkeys to check
            with_odata_id   include odata id? id should be in the selected fields
            include_etag    etag metho should be defined in class model and given in constructor as parameter

        """ 
        def serialize(obj):
            #Internal function for recursive processing            
            data = obj.__data__.copy()

            #Support for auto expanding FK definitions in the model
            if self.expand_complex:
                for field_name, field_object in self.navigated_class._meta.fields.items():
                    if isinstance(field_object, ForeignKeyField):
                        data[field_name] = getattr(obj,field_name).__data__.copy()

            if with_odata_id:
                name = self._extract_before_parenthesis(self.path_classes[0].path)
                data["@odata.id"] = f"{name}({data['id']})"
            if include_etag:
                f = getattr(obj,self.etag_callable)
                data["@odata.etag"] = f()

            
            difference = None


            if self.parser.select:
                #Hide fiedls which should be always selected but not in the list, like id    
                difference = [item for item in self.select_always if item not in self.parser.select]
                data = {
                    k: '' if k in difference else v
                    for k, v in data.items()
                }


            for model,exp,nested in self.expands:
                
                self.write_log(f"Expanding {exp} {nested} ")

                child_include_etag = include_etag
                child_etag_callable = self.etag_callable
                child_include_etag = include_etag
                child_with_odata_id = with_odata_id

                if model not in self.models:
                    child_include_etag = False
                    child_etag_callable = None
                    child_include_etag = False
                    child_with_odata_id = False
                    child_models = [model]
                    child_expandabel = []
                else:
                    child_models = self.models
                    child_expandabel = self.expandable



                # Build a filtered query for the related model
                fk_field, fk_model = self.get_field_name_from_backref(model, exp)


                if not fk_field:
                    raise Exception(f"Cannot resolve backref field for {exp}")

                if not nested:
                    nested = ""

                #build a query object for the recursive backref processing
                sub_tree = PeeweeODataQuery( child_models, "/" + model.__name__.lower() +"s?" + nested,expandable=child_expandabel,etag_callable=child_etag_callable,select_always=self.select_always)
                sub_tree.set_hidden_fields(self.hidden)
                sub_tree.set_search_fields(self.search_fields)
                sub_tree.set_expand_complex(self.expand_complex)
                filtered_query = sub_tree.query(join=[fk_model],where=[fk_field == obj.id])
                # Serialize the filtered and expanded result
                data[exp] = sub_tree.peewee_result_to_dict_or_list(filtered_query,include_etag=child_include_etag,with_odata_id=child_with_odata_id)

                return data

            # Hide fields:
            data = {
                k: '' if k in self.hidden else v
                for k, v in data.items()
            }


            return data



        if isinstance(query_result, Model):
            result_list = [serialize(query_result)]
        else:
            if self.parser.count == True:
                return str(query_result)
            
            result_list = [serialize(obj) for obj in query_result]


        if len(result_list) == 1:
            return result_list[0]
        
        if type(result_list) == list:
            final_res = { "value" : result_list}
            if self.skiptoken_size != 0 and self.next_page != -1:
                final_res["@odata.nextLink"] = self._replace_skiptoken(str(self.next_page))

        return final_res






