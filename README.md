[![codecov](https://codecov.io/gh/Devilx85/odata-pyq/branch/main/graph/badge.svg)](https://codecov.io/gh/Devilx85/odata-pyq)
[![Python Tests and Badge](https://github.com/Devilx85/odata-pyq/actions/workflows/python-app.yml/badge.svg)](https://github.com/Devilx85/odata-pyq/actions/workflows/python-app.yml)
-----

# OData Parser + Peewee Integration

A comprehensive Python library that provides OData v4 query parsing and seamless integration with Peewee ORM, enabling RESTful API endpoints with full OData query capabilities.

## 🚀 Features

### Complete OData v4 Query Support

  - **$filter** - Advanced filtering with Boolean conditions and logical operators (AND/OR/NOT).
  - **$select** - Field selection with comma-separated lists.
  - **$expand** - Include related entities inline with support for nested parameters and sub-queries.
  - **$orderby** - Multi-field sorting with ascending/descending directions.
  - **$top** - Result limiting for pagination.
  - **$skip** - Offset-based pagination.
  - **$skiptoken** - Server-side pagination with automatic next-link generation.
  - **$count** - Entity count requests.
  - **$search** - Full-text search across specified fields.
  - **$format** - Response media type specification (parser support).

### Advanced Filtering Capabilities

  - **Comparison operators**: `eq`, `ne`, `gt`, `lt`, `ge`, `le`.
  - **Arithmetic operators**: `add`, `sub`, `mul`, `div`
  - **String functions**: `contains()`, `startswith()`, `endswith()`.
  - **Logical operators**: `and`, `or`, `not`.
  - **Date operators**: `now()`
  - **Complex nested expressions** with parentheses.
  - **Field navigation** through relationships (e.g., `order/customer/name`).

### Full CRUD Operations

  - **GET** - Query entities with complete OData parameter support.
  - **POST** - Create new entities with relationship handling.
  - **PUT/PATCH** - Update existing entities (full or partial updates).
  - **DELETE** - Remove entities with proper validation.

### Enterprise-Ready Features

  - **Relationship Navigation** - Foreign keys and backref traversal.
  - **Circular Reference Protection** - Automatic detection and prevention.
  - **Access Control** - Model-level permissions for Browse, modification, and expansion.
  - **Comprehensive Logging** - Full operation tracking and debugging.
  - **ETag Support** - Optimistic concurrency control.
  - **OData Metadata** - Automatic CSDL/XML metadata generation.
  - **Hidden Fields** - Security through field visibility control.
  - **Search Integration** - Configurable full-text search across model fields.

-----

## 📦 Installation

```bash
pip install peewee lark
```

-----

## 🏃‍♂️ Quick Start

### Model Definition

```python
from peewee import *
from odata_parser import ODataParser
from pewee_qodata import PeeweeODataQuery, DataType

# Define your Peewee models
class User(Model):
    name = CharField()
    email = CharField()
    age = IntegerField()
    created_date = DateTimeField()
    
class Order(Model):
    user = ForeignKeyField(User, backref='orders')
    product = CharField()
    amount = DecimalField()
    created_date = DateTimeField()
```

### Basic Queries

```python
# Simple pagination
# GET /users?$top=10&$skip=20
query = PeeweeODataQuery([User], "/users?$top=10&$skip=20")
results = query.to_odata_response(query.query())

# Advanced filtering
# GET /users?$filter=age gt 25 and contains(name,'john')
query = PeeweeODataQuery([User], "/users?$filter=age gt 25 and contains(name,'john')")
results = query.to_odata_response(query.query())

# Field selection with sorting
# GET /users?$select=name,email&$orderby=created_date desc
query = PeeweeODataQuery([User], "/users?$select=name,email&$orderby=created_date desc")
results = query.to_odata_response(query.query())
```

### Relationship Expansion

```python
# Simple expansion
# GET /users?$expand=orders
query = PeeweeODataQuery([User], "/users?$expand=orders", expandable=[Order])
results = query.to_odata_response(query.query())

# Nested expansion with sub-queries
# GET /users?$expand=orders($filter=amount gt 100;$orderby=created_date desc;$top=5)
query = PeeweeODataQuery(
    [User], 
    "/users?$expand=orders($filter=amount gt 100;$orderby=created_date desc;$top=5)",
    expandable=[Order]
)
results = query.to_odata_response(query.query())
```

### Navigation and Entity Access

```python
# Access specific entity
# GET /users(123)
query = PeeweeODataQuery([User], "/users(123)")
user = query.to_odata_response(query.query())

# Navigate relationships
# GET /users(123)/orders?$filter=amount gt 50
query = PeeweeODataQuery([User], "/users(123)/orders?$filter=amount gt 50", expandable=[Order])
orders = query.to_odata_response(query.query())
```

-----

## 🔧 Advanced Configuration

### Security and Access Control

```python
# Configure expandable models (read-only access)
expandable = [Order, Product]  # Can be expanded but not modified directly
query = PeeweeODataQuery([User], url, expandable=expandable)

# Hide sensitive fields
query.set_hidden_fields(['password_hash', 'internal_notes'])

# Configure search fields for $search parameter
query.set_search_fields(['name', 'email', 'description'])
```

### Server-Side Pagination

```python
# Enable automatic pagination with skip tokens
query.set_skiptoken(100)  # Max 100 records per page
results = query.to_odata_response(query.query())
# Automatically includes @odata.nextLink when more data available
```

### Logging and Debugging

```python
import logging

logger = logging.getLogger(__name__)
query = PeeweeODataQuery([User], url, logger=logger)
# Comprehensive logging of query construction and execution
```

-----

## 🔨 CRUD Operations

### Create Entity

```python
# POST /users
query = PeeweeODataQuery([User], "/users")
new_user = query.create({
    'name': 'John Doe',
    'email': 'john@example.com',
    'age': 30
}, default_field_values={'status': 'active'})
```

### Update Operations

```python
# Full update (PUT)
query = PeeweeODataQuery([User], "/users(123)")
updated_user = query.update({
    'name': 'John Smith',
    'email': 'johnsmith@example.com',
    'age': 31
})

# Partial update (PATCH)
updated_user = query.update({'age': 32}, patch=True)
```

### Delete Entity

```python
# DELETE /users(123)
query = PeeweeODataQuery([User], "/users(123)")
deleted_user = query.delete()
```

-----

## 🏗️ Architecture

### Core Components

  - **ODataURLParser** - A utility for parsing OData query strings, handling special cases like nested parentheses and escaped characters.
  - **ODataFilterTransformer** - A transformer class that converts OData `$filter` expressions into a tree of logical and comparison operators, which can then be used to build a Peewee query.
  - **ODataPathTransformer** - A transformer that parses the OData URL path to identify the entity set, key predicates, and navigation segments.
  - **ODataParser** - The main class that orchestrates the parsing of a full OData URL, extracting the path and query parameters like `$filter`, `$expand`, `$select`, etc., using the specialized parsers.
  - **PeeweeODataQuery** - The central engine that takes the parsed OData request and builds the corresponding Peewee ORM query, handling joins, filters, sorting, pagination, and expansions.
  - **PeeweeODataMeta** - A class responsible for generating OData v4 CSDL (Common Schema Definition Language) metadata from Peewee models, describing the service's available entities and their properties.

### The `ODataParser` Class in Detail

The `ODataParser` class is the core component that processes a full OData URL, extracting both the navigation path and the various query parameters. It uses specialized parsers for complex parameters like `$filter` and `$expand` to correctly interpret the request.

After parsing, the `ODataParser` populates its internal attributes with the structured query data, which is then used by the `PeeweeODataQuery` class to build a Peewee query.

**Key Attributes After Parsing:**

  - `self.parsed_path`: A list of dictionaries representing the navigation path, including entity names and key predicates.
  - `self.filter`: A tree-like object representing the parsed `$filter` expression.
  - `self.select`: A list of strings for the fields to be selected.
  - `self.expand`: A list of tuples, where each tuple contains an entity to expand and its nested parameters.
  - `self.orderby`: A dictionary with field names as keys and sort directions as values.
  - `self.top`, `self.skip`: Integers for pagination limits and offsets.
  - `self.count`: A boolean indicating whether a count is requested.

### Filter Expression Structure

The `ODataParser` and its `ODataFilterTransformer` convert a `$filter` string into a structured object that represents the logical tree of the expression. The structure is composed of several custom classes:

  - **`ODataLogOperator`**: Represents a logical operation (`and`, `or`, `not`). It has `left` and `right` attributes that hold other expressions, allowing for nested logic. For a `not` operator, only the `right` attribute is used.
  - **`ODataOperator`**: Represents a comparison operation (`eq`, `ne`, `gt`, `lt`, `ge`, `le`). It has attributes `a` and `b` for the two sides of the comparison, which can be fields, values, or other expressions.
  - **`ODataFunction`**: Represents a function call, such as `contains`, `startswith`, or `endswith`. It stores the function `name` and a list of `args`.
  - **`ODataField`**: Represents a field or property name within the filter expression.
  - **`ODataPrimitve`**: Represents a literal value like a string, number, boolean, or `null`.

This tree-like structure enables the `PeeweeODataQuery` to recursively traverse the expression and build the corresponding Peewee `where` conditions.

#### Example 1: Simple Equality

**OData URL:** `/users?$filter=name eq 'John'`
The parser outputs an `ODataOperator` object with:

  - `name`: `'eq'`
  - `a`: `ODataField` with `name='name'`
  - `b`: `ODataPrimitve` with `value='John'`

#### Example 2: Logical Operators

**OData URL:** `/products?$filter=price gt 50 and stock gt 10`
The parser outputs an `ODataLogOperator` object with:

  - `name`: `'and'`
  - `left`: an `ODataOperator` for `price gt 50`
  - `right`: an `ODataOperator` for `stock gt 10`

#### Example 3: Nested Expressions and Functions

**OData URL:** `/users?$filter=contains(name,'smith') or endswith(email,'.com')`
The parser outputs an `ODataLogOperator` object with:

  - `name`: `'or'`
  - `left`: an `ODataFunction` for `contains`
  - `right`: an `ODataFunction` for `endswith`

### Query Processing Pipeline

1.  **URL Parsing** - The `ODataParser` and `ODataURLParser` extract OData parameters and navigation paths from the incoming URL.
2.  **Model Resolution** - `PeeweeODataQuery` resolves the entity types and relationships based on the URL path, using helper functions like `find_model_rel` to discover foreign keys and backrefs.
3.  **Security Validation** - Configured access controls and permissions are applied to prevent unauthorized operations or expansions.
4.  **Query Construction** - The parsed parameters are translated into Peewee query components. For example, the `$filter` expression is converted into `peewee.Expression` objects, and `$expand` generates necessary joins.
5.  **Result Processing** - The `to_odata_response` method formats the Peewee query result into a dictionary or list of dictionaries that adheres to OData conventions.
6.  **Response Generation** - The final response includes metadata, ETags, and pagination links like `@odata.nextLink` for server-side pagination.

-----

## 📊 Advanced Examples

### Complex Filtering

```python
# Multiple conditions with grouping
url = "/users?$filter=(age gt 18 and age lt 65) and (contains(name,'John') or contains(email,'john'))"

# Date-based filtering
url = "/orders?$filter=created_date ge '2023-01-01T00:00:00Z' and amount gt 100"

```

### Multi-Level Expansion

```python
# Deep relationship expansion
url = "/users?$expand=orders($expand=items($select=name,price&$orderby=price desc))"

# Conditional expansion
url = "/customers?$expand=orders($filter=status eq 'active'&$expand=items)"
```

### Metadata Generation

```python
from peewee_metadata import PeeweeODataMeta

# Generate OData v4 CSDL metadata
metadata_xml = PeeweeODataMeta.create_multi_model_metadata(
    model_classes=[User, Order, Product],
    namespace="MyService",
    container_name="MyContainer"
)
```

-----

## ⚙️ Configuration Options

### Constructor Parameters

  - **models** - Primary models that can be browsed and modified.
  - **expandable** - Models that can only be expanded (read-only).
  - **logger** - Logger instance for operation tracking.
  - **etag\_callable** - Method to generate ETags for concurrency control.
  - **select\_always** - Fields always included in queries (e.g., 'id', 'modified\_date').

### Runtime Configuration

```python
query.set_expand_complex(False)  # Disable automatic FK expansion
query.add_restriction(User, [User.active == True])  # Add model-level filters
```

-----

## 🚨 Current Limitations

  - **Single Primary Key** - Only supports models with single-column primary keys.
  - **Deep Structure Operations** - Complex nested create/update operations not yet supported.
  - **Advanced OData Functions** - Some OData v4 functions are not implemented.
  - **Performance** - Complex nested expansions may require optimization for large datasets.

-----

## 🤝 Contributing

We welcome contributions\! Please ensure:

1.  **Code Quality** - Follow existing patterns and add comprehensive tests
2.  **Documentation** - Update README and inline documentation
3.  **Performance** - Consider performance implications of changes
4.  **Backward Compatibility** - Maintain API compatibility where possible

## 📞 Support

  - **Issues**: GitHub issue tracker
  - **Email**: lmartynov@tuta.com
  - **Documentation**: See inline code documentation for detailed API reference

-----

**Built with ❤️ for the Python community**
