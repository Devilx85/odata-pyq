# OData Parser & Peewee Integration

A Python library that provides OData query parsing and seamless integration with Peewee ORM, enabling RESTful API endpoints with OData query capabilities.

## Features

### OData Query Support

- **$filter** - Filter results with Boolean conditions and logical operators (AND/OR)
- **$select** - Choose specific fields to include in responses (supported only as sinmple list , separated by comma)
- **$expand** - Include related entities inline (supports nested parameters)
- **$orderby** - Sort results by one or more properties
- **$top** - Limit the number of results returned
- **$skip** - Skip a specified number of results for pagination
- **$count** - Request entity counts (currently only parser!)
- **$search** - Full-text search support (currently only parser and no logical operations , just a string!)
- **$format** - Specify response media type (currently only parser!)

### Filter Operations

- **Comparison operators**: `eq`, `ne`, `gt`, `lt`, `ge`, `le`
- **String functions**: `contains()`, `startswith()`, `endswith()`
- **Logical operators**: `and`, `or`,`not`

### CRUD Operations

- **GET** - Query entities with full OData parameter support
- **POST** - Create new entities
- **PUT/PATCH** - Update existing entities
- **DELETE** - Remove entities

**IMPORTANT!**
PeeweeODataQuery can be used only with single primary key "id", compound keys are not yet supported.

### Advanced Features

- Complex nested URL parsing with parentheses and ampersands
- Foreign key and backref relationship navigation
- Circular reference detection and prevention
- Model access control via allowed objects to browse+modify and expand 
- Comprehensive logging support
- etag and odata id on-fly inclusion

## Installation

```bash
pip install peewee lark
```

## Quick Start

### Basic Setup

```python
from peewee import *
from odata_parser import ODataParser
from pewee_qodata import PeeweeODataQuery, DataType

# Define your Peewee models
class User(Model):
    name = CharField()
    email = CharField()
    age = IntegerField()
    
class Order(Model):
    user = ForeignKeyField(User, backref='orders')
    product = CharField()
    amount = DecimalField()
    created_date = DateTimeField()
```

### Query Examples

#### Simple Query
```python
# GET /users?$top=10&$skip=20
query = PeeweeODataQuery([User], "/users?$top=10&$skip=20")
results = query.peewee_result_to_dict_or_list(query.query())
```

#### Filtering
```python
# GET /users?$filter=age gt 25 and name eq 'John'
query = PeeweeODataQuery(
    [User], 
    "/users?$filter=age gt 25 and name eq 'John'"
)
results = query.peewee_result_to_dict_or_list(query.query())
```

#### String Functions
```python
# GET /users?$filter=contains(name,'john')
query = PeeweeODataQuery(
    [User],
    "/users?$filter=contains(name,'john')"
)
results = query.peewee_result_to_dict_or_list(query.query())
```

#### Field Selection
```python
# GET /users?$select=name,email
query = PeeweeODataQuery(
    [User],
    "/users?$select=name,email"
)
results = query.peewee_result_to_dict_or_list(query.query())
```

#### Sorting
```python
# GET /users?$orderby=age desc,name asc
query = PeeweeODataQuery(
    [User],
    "/users?$orderby=age desc,name asc"
)
results = query.peewee_result_to_dict_or_list(query.query())
```

#### Expanding Related Entities
```python
# GET /users?$expand=orders
query = PeeweeODataQuery(
    [User],
    "/users?$expand=orders",
    expandable=[Order]   #Can be expanded but not navigated from root/or modified
)
results = query.peewee_result_to_dict_or_list(query.query())
```

#### Nested Expand with Parameters
```python
# GET /users?$expand=orders($filter=amount gt 100;$orderby=created_date desc)
query = PeeweeODataQuery(
    [User],
    "/users?$expand=orders($filter=amount gt 100;$orderby=created_date desc)",
    expandable=[Order]
)
results = results = query.peewee_result_to_dict_or_list(query.query())(query.query())
```

### Navigation Examples

#### Entity by ID
```python
# GET /users(123)
query = PeeweeODataQuery([User], "/users(123)")
user = query.peewee_result_to_dict_or_list(query.query())
```

#### Related Entity Navigation
```python
# GET /users(123)/orders
query = PeeweeODataQuery(
    [User], 
    "/users(123)/orders",
    expandable=[ Order]
)
orders = query.peewee_result_to_dict_or_list(query.query())
```

### CRUD Operations

#### Create Entity
```python
# POST /users
query = PeeweeODataQuery([User], "/users")
new_user = query.create({
    'name': 'John Doe',
    'email': 'john@example.com',
    'age': 30
})
```

#### Update Entity (PUT)
```python
# PUT /users(123)
query = PeeweeODataQuery([User], "/users(123)")
updated_user = query.update({
    'name': 'John Smith',
    'email': 'johnsmith@example.com',
    'age': 31
})
```

#### Partial Update (PATCH)
```python
# PATCH /users(123)
query = PeeweeODataQuery([User], "/users(123)")
updated_user = query.update({'age': 32}, patch=True)
```

#### Delete Entity
```python
# DELETE /users(123)
query = PeeweeODataQuery([User], "/users(123)")
deleted_user = query.delete()
```

## Advanced Usage

### Security and Access Control

```python
# Restrict access to specific models
expandable = [User, Order]  # models list and only these models can be accessed or viewed. Expandable models cannot be modified and do not include eatags or odata ids
query = PeeweeODataQuery([User], url, expandable=expandable)
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)
query = PeeweeODataQuery([User], url,  logger=logger)
```

### Custom Field Values

```python
# Create with default and rewrite values
query.create(
    data={'name': 'John'},
    default_field_values={'status': 'active'},
    rewrite_filed_values={'created_by': current_user.id}
)
```

### Complex Filtering Examples

```python
# Multiple conditions with logical operators
# $filter=(age gt 18 and age lt 65) and contains(name,'John')
url = "/users?$filter=(age gt 18 and age lt 65) and contains(name,'John')"
query = PeeweeODataQuery([User], url])

# String operations
# $filter=startswith(email,'john') or endswith(email,'@company.com')
url = "/users?$filter=startswith(email,'john') or endswith(email,'@company.com')"
query = PeeweeODataQuery([User], url)
```

## API Reference

### ODataParser

Parses OData URLs and extracts query parameters.

```python
parser = ODataParser("http://example.com/users?$filter=age gt 25")
parser.run()
# Access parsed components
print(parser.filter)  # Parsed filter expression
print(parser.top)     # Top parameter value
print(parser.skip)    # Skip parameter value
```

### PeeweeODataQuery

Main class for executing OData operations on Peewee models.

#### Constructor Parameters

- **models** (Model): Peewee models to browse (can be expandable if have backreferences)
- **url** (str): OData URL to parse
- **expandable** (list): List of allowed model classes to expand only
- **logger** (Logger, optional): Logger for operation tracking
- **etag_callable** a method of model to dynamically generate etag
- **select_always** fields to request , even if they are not included in select parameter (e.g id , etag etc)
#### Methods

- **query(where=[], join=[])**: Execute SELECT query
- **create(data={}, rewrite_filed_values={}, default_field_values={})**: Create new entity
- **update(data={}, rewrite_filed_values={}, default_field_values={}, patch=False)**: Update entity
- **delete()**: Delete entity
- **peewee_result_to_dict_or_list(query_result,with_odata_id=True,include_etag=False)**: Convert results to dict/list format (idata and etag support)

## Limitations

- Currently supports single primary key entities only
- Deep structure creation/updates not yet supported
- Relationship operations and OData functions partially implemented
- Complex nested expand operations may have performance implications

## Etags and Odata id tags in result

To correctly include odata id tag in the result list you have to include always id field, and set with_odata_id parameter to 
True in peewee_result_to_dict_or_list. 

Etags you can generate out of model itself, providing in constructor etag_callable parameter. A good example is generating
etag from id and last modification time or version. in this case both fields you need to select in the model via select_always
list. This ensures that fields are always in the select statement, they will be hidden in case select query does not contain 
them.

## Contributing

Contributions are welcome! Please ensure:

1. Code follows existing patterns and conventions
2. Add tests for new features
3. Update documentation for API changes
4. Handle edge cases and provide appropriate error messages



## Support

For issues and questions, please use the GitHub issue tracker or contact the maintainers.
