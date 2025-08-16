[![codecov](https://codecov.io/gh/Devilx85/odata-pyq/branch/main/graph/badge.svg)](https://codecov.io/gh/Devilx85/odata-pyq)
[![Python Tests and Badge](https://github.com/Devilx85/odata-pyq/actions/workflows/python-app.yml/badge.svg)](https://github.com/Devilx85/odata-pyq/actions/workflows/python-app.yml)

# OData Parser + Peewee Integration

A comprehensive Python library that provides OData v4 query parsing and seamless integration with the Peewee ORM, enabling RESTful API endpoints with full OData query capabilities.

This library is composed of two main layers: a powerful, standalone **OData Parser** for deconstructing any OData URL, and a **Peewee Query Engine** that translates the parsed output into efficient database queries.

-----

## 🚀 Features

### Complete OData v4 Query Support

  * **$filter**: Advanced filtering with Boolean conditions and logical operators (`and`, `or`, `not`).
  * **$select**: Field selection with comma-separated lists.
  * **$expand**: Includes related entities inline, with support for nested parameters and sub-queries.
  * **$orderby**: Multi-field sorting with ascending (`asc`) and descending (`desc`) directions.
  * **$top** & **$skip**: Limit and offset for client-side pagination.
  * **$skiptoken**: Server-side, token-based pagination with automatic `@odata.nextLink` generation.
  * **$count**: Requests a total count of matching entities.
  * **$search**: Full-text search across specified model fields.

### Advanced Filtering Capabilities

  * **Comparison Operators**: `eq`, `ne`, `gt`, `lt`, `ge`, `le`.
  * **Arithmetic Operators**: `add`, `sub`, `mul`, `div`.
  * **String Functions**: `contains()`, `startswith()`, `endswith()`.
  * **Date Functions**: `now()`.
  * **Logical Operators**: `and`, `or`, `not`.
  * **Complex Nested Expressions** with parentheses.
  * **Field Navigation** through relationships (e.g., `order/customer/name`).

### Enterprise-Ready Features

  * **Full CRUD Operations**: Complete support for GET, POST, PUT, PATCH, and DELETE.
  * **Composite Key Support**: Natively handles models with multiple primary keys or designated unique keys for entity access.
  * **Relationship Navigation**: Seamlessly traverses foreign keys and back-references in URL paths.
  * **Access Control**: Define which models are browsable, expandable, or modifiable.
  * **Circular Reference Protection**: Automatically detects and prevents circular dependencies in URL paths.
  * **Recursive Expansion Control**: Set a maximum depth for `$expand` operations to protect against performance issues.
  * **Hidden Fields**: Enhance security by controlling field visibility in the final JSON output.
  * **Comprehensive Logging**: Full operation tracking and debugging via a standard logger instance.

-----

## 📦 Installation

```bash
pip install peewee lark-parser python-dateutil
```

-----

## 🏃‍♂️ Quick Start

### 1\. Define Your Peewee Models

```python
from peewee import *
from pewee_qodata import PeeweeODataQuery
import datetime

class User(Model):
    id = AutoField()
    name = CharField()
    email = CharField(unique=True)
    age = IntegerField()
    is_active = BooleanField(default=True)
    created_date = DateTimeField(default=datetime.datetime.now)

class Order(Model):
    id = AutoField()
    user = ForeignKeyField(User, backref='orders')
    product = CharField()
    amount = DecimalField()
    created_date = DateTimeField(default=datetime.datetime.now)

MODELS = [User, Order]
```

### 2\. Perform Queries

```python
# GET /users?$select=name,email&$expand=orders($filter=amount gt 100)
url = "/users?$select=name,email&$expand=orders($filter=amount gt 100)"
query = PeeweeODataQuery(MODELS, url, expandable=[Order])
results = query.to_odata_response(query.query())
```

### 3\. Navigate to Entities

```python
# Access a user by their primary key: /users(123)
query_by_id = PeeweeODataQuery(MODELS, "/users(123)")
user = query_by_id.to_odata_response(query_by_id.query())

# Access by a unique field: /users(email='john@example.com')
query_by_email = PeeweeODataQuery(MODELS, "/users(email='john@example.com')")
query_by_email.set_model_ufield_as_key(User, 'email')
user = query_by_email.to_odata_response(query_by_email.query())
```

-----

## 🔨 CRUD Operations

### Create (POST)

```python
# POST /users
query = PeeweeODataQuery(MODELS, "/users")
new_user = query.create({'name': 'Jane Doe', 'email': 'jane@example.com', 'age': 30})
```

### Update (PUT / PATCH)

```python
# Partial update: PATCH /users(123)
query = PeeweeODataQuery(MODELS, "/users(123)")
updated_user = query.update({'age': 32}, patch=True)
```

### Delete (DELETE)

```python
# DELETE /users(123)
query = PeeweeODataQuery(MODELS, "/users(123)")
deleted_user = query.delete()
```

-----

## 🔧 Advanced Configuration

```python
query = PeeweeODataQuery(MODELS, "/users?$top=5")

# Enable server-side pagination
query.set_skiptoken(100)

# Hide sensitive fields from the output
query.set_hidden_fields(['password_hash'])

# Configure searchable fields for $search
query.set_search_fields(['name', 'email'])

# Set max $expand depth
query.set_max_expand(3)

# Add global 'where' conditions for a model
query.add_restricition(User, [User.is_active == True])
```

-----

## 🏗️ Architecture & Parser Details

The library's power comes from its two-layer architecture: the parser and the query engine.

### Core Components

  * **`ODataURLParser`**: A utility that intelligently splits OData query strings, properly handling nested parentheses and quotes found in complex `$expand` and `$filter` clauses.
  * **`ODataParser`**: The primary parser that uses the **Lark** library with a formal OData grammar to transform a URL into a structured Python object tree.
  * **`PeeweeODataQuery`**: The main engine that consumes the object tree from the parser and builds the corresponding Peewee ORM query.

-----

### Understanding the `$filter` Expression Tree

When `ODataParser` processes a `$filter` string, it doesn't just validate it; it transforms it into a nested object structure—an **expression tree**. This tree is then easy for the `PeeweeODataQuery` engine to walk through and convert into a database query.

The tree is composed of the following object types:

  * `ODataLogOperator`: Represents a logical operation: `and`, `or`, `not`. It has `left` and `right` attributes that hold the next nodes in the tree.
  * `ODataOperator`: Represents a comparison (`eq`, `ne`, `gt`, etc.) or arithmetic (`add`, `sub`, etc.) operation. It has `a` and `b` attributes for the two operands.
  * `ODataFunction`: Represents a function call like `contains()` or `now()`. It stores the function `name` and a list of `args`.
  * `ODataField`: A leaf node representing a model's field or property (e.g., `name`).
  * `ODataPrimitve`: A leaf node representing a literal value (e.g., the string `'John'` or the number `25`).

#### Example Breakdown

Let's see how a complex filter is deconstructed.

**OData URL Filter:**
`$filter=(age gt 25 and contains(name, 'John')) or startswith(email, 'admin')`

**Parsed Expression Tree:**
This string is parsed into the following nested object structure:

```
ODataLogOperator(name='or')
├── left: ODataLogOperator(name='and')
│   ├── left: ODataOperator(name='gt')
│   │   ├── a: ODataField(name='age')
│   │   └── b: ODataPrimitve(value=25)
│   └── right: ODataFunction(name='contains')
│       ├── args[0]: ODataField(name='name')
│       └── args[1]: ODataPrimitve(value='John')
└── right: ODataFunction(name='startswith')
    ├── args[0]: ODataField(name='email')
    └── args[1]: ODataPrimitve(value='admin')
```

The `PeeweeODataQuery` engine can then recursively traverse this tree to build the final Peewee expression: `((User.age > 25) & (User.name.contains('John'))) | (User.email.startswith('admin'))`.

### Standalone Parser Usage

You can use the parser directly to deconstruct and analyze any OData URL.

```python
from odata.odata_parser import ODataParser

# A complex OData URL
url = "/users?$filter=(age gt 25 and contains(name, 'John')) or startswith(email, 'admin')&$orderby=age desc"

# 1. Initialize and run the parser
parser = ODataParser(url)
parser.run()

# 2. Inspect the structured results
print(f"Path: {parser.parsed_path}")
# Output: Path: [{'entity': 'users'}]

print(f"Order By: {parser.orderby}")
# Output: Order By: {'age': 'desc'}

# 3. Access the filter tree
filter_tree = parser.filter
print(f"Top-level operator: {filter_tree.name}")
# Output: Top-level operator: or

# You can now traverse the tree as described above
left_side = filter_tree.left
print(f"Left side operator: {left_side.name}")
# Output: Left side operator: and
```

-----

## 🚨 Limitations

  * **Deep Structure Mutations**: Complex nested create/update operations in a single request are not yet supported.
  * **Advanced OData Functions**: Some OData v4 functions beyond string, date, and arithmetic operations are not implemented.
  * **Performance**: While optimized, complex and deeply nested expansions on very large datasets may require careful schema design and indexing.

-----

## 🤝 Contributing & Support

  * **Issues**: GitHub issue tracker
  * **Email**: lmartynov@tuta.com
  * **Documentation**: See inline code documentation for detailed API reference.
