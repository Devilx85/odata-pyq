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
- **Logical operators**: `and`, `or`

### CRUD Operations

- **GET** - Query entities with full OData parameter support
- **POST** - Create new entities
- **PUT/PATCH** - Update existing entities
- **DELETE** - Remove entities

### Advanced Features

- Complex nested URL parsing with parentheses and ampersands
- Foreign key and backref relationship navigation
- Circular reference detection and prevention
- Model access control via allowed objects list
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
from pewee_qodata import PeweeODataQuery, DataType

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
query = PeweeODataQuery(User, "/users?$top=10&$skip=20", allowed_objects=[User])
results = query.peewee_result_to_dict_or_list(query.query())
```

#### Filtering
```python
# GET /users?$filter=age gt 25 and name eq 'John'
query = PeweeODataQuery(
    User, 
    "/users?$filter=age gt 25 and name eq 'John'",
    allowed_objects=[User]
)
results = query.peewee_result_to_dict_or_list(query.query())
```

#### String Functions
```python
# GET /users?$filter=contains(name,'john')
query = PeweeODataQuery(
    User,
    "/users?$filter=contains(name,'john')",
    allowed_objects=[User]
)
results = query.peewee_result_to_dict_or_list(query.query())
```

#### Field Selection
```python
# GET /users?$select=name,email
query = PeweeODataQuery(
    User,
    "/users?$select=name,email",
    allowed_objects=[User]
)
results = query.peewee_result_to_dict_or_list(query.query())
```

#### Sorting
```python
# GET /users?$orderby=age desc,name asc
query = PeweeODataQuery(
    User,
    "/users?$orderby=age desc,name asc",
    allowed_objects=[User]
)
results = query.peewee_result_to_dict_or_list(query.query())
```

#### Expanding Related Entities
```python
# GET /users?$expand=orders
query = PeweeODataQuery(
    User,
    "/users?$expand=orders",
    allowed_objects=[User, Order]
)
results = query.peewee_result_to_dict_or_list(query.query())
```

#### Nested Expand with Parameters
```python
# GET /users?$expand=orders($filter=amount gt 100;$orderby=created_date desc)
query = PeweeODataQuery(
    User,
    "/users?$expand=orders($filter=amount gt 100;$orderby=created_date desc)",
    allowed_objects=[User, Order]
)
results = results = query.peewee_result_to_dict_or_list(query.query())(query.query())
```

### Navigation Examples

#### Entity by ID
```python
# GET /users(123)
query = PeweeODataQuery(User, "/users(123)", allowed_objects=[User])
user = query.peewee_result_to_dict_or_list(query.query())
```

#### Related Entity Navigation
```python
# GET /users(123)/orders
query = PeweeODataQuery(
    User, 
    "/users(123)/orders",
    allowed_objects=[User, Order]
)
orders = query.peewee_result_to_dict_or_list(query.query())
```

### CRUD Operations

#### Create Entity
```python
# POST /users
query = PeweeODataQuery(User, "/users", allowed_objects=[User])
new_user = query.create({
    'name': 'John Doe',
    'email': 'john@example.com',
    'age': 30
})
```

#### Update Entity (PUT)
```python
# PUT /users(123)
query = PeweeODataQuery(User, "/users(123)", allowed_objects=[User])
updated_user = query.update({
    'name': 'John Smith',
    'email': 'johnsmith@example.com',
    'age': 31
})
```

#### Partial Update (PATCH)
```python
# PATCH /users(123)
query = PeweeODataQuery(User, "/users(123)", allowed_objects=[User])
updated_user = query.update({'age': 32}, patch=True)
```

#### Delete Entity
```python
# DELETE /users(123)
query = PeweeODataQuery(User, "/users(123)", allowed_objects=[User])
deleted_user = query.delete()
```

## Advanced Usage

### Security and Access Control

```python
# Restrict access to specific models
allowed_models = [User, Order]  # Only these models can be accessed
query = PeweeODataQuery(User, url, allowed_objects=allowed_models)
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)
query = PeweeODataQuery(User, url, allowed_objects=[User], logger=logger)
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
query = PeweeODataQuery(User, url, allowed_objects=[User])

# String operations
# $filter=startswith(email,'john') or endswith(email,'@company.com')
url = "/users?$filter=startswith(email,'john') or endswith(email,'@company.com')"
query = PeweeODataQuery(User, url, allowed_objects=[User])
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

### PeweeODataQuery

Main class for executing OData operations on Peewee models.

#### Constructor Parameters

- **initial_class** (Model): Starting Peewee model class
- **url** (str): OData URL to parse
- **allowed_objects** (list): List of allowed model classes
- **logger** (Logger, optional): Logger for operation tracking
- **etag_callable** a method of model to dynamically generate etag
- **select_always** fields to select , even if they are not included in select (e.g id , etag etc)
#### Methods

- **query(where=[], join=[])**: Execute SELECT query
- **create(data={}, rewrite_filed_values={}, default_field_values={})**: Create new entity
- **update(data={}, rewrite_filed_values={}, default_field_values={}, patch=False)**: Update entity
- **delete()**: Delete entity
- **peewee_result_to_dict_or_list(query_result)**: Convert results to dict/list format

## Limitations

- Currently supports single primary key entities only
- Deep structure creation/updates not yet supported
- Relationship operations and OData functions partially implemented
- Complex nested expand operations may have performance implications

## Etags and Odata id tags in result

To correctly perform operation you need include always id, and set with_odata_id to Trur in peewee_result_to_dict_or_list. 
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
