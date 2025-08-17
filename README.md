[![codecov](https://codecov.io/gh/Devilx85/odata-pyq/branch/main/graph/badge.svg)](https://codecov.io/gh/Devilx85/odata-pyq)
[![Python Tests and Badge](https://github.com/Devilx85/odata-pyq/actions/workflows/python-app.yml/badge.svg)](https://github.com/Devilx85/odata-pyq/actions/workflows/python-app.yml)

# OData Parser + Peewee Integration

A comprehensive Python library that provides OData v4 query parsing and seamless integration with the Peewee ORM, enabling RESTful API endpoints with full OData query capabilities.

This library is composed of two main layers: a powerful, standalone **OData Parser** for deconstructing any OData URL, and a **Peewee Query Engine** that translates the parsed output into efficient database queries.

-----

## 🚀 Features

### Complete OData v4 Query Support

  * **`$filter`**: Advanced filtering with Boolean conditions and logical operators (`and`, `or`, `not`).
  * **`$select`**: Field selection to shape the JSON output.
  * **`$expand`**: Includes related entities inline, with full support for nested parameters and sub-queries (e.g., nested `$filter`, `$select`, `$orderby`).
  * **`$orderby`**: Multi-field sorting with ascending (`asc`) and descending (`desc`) directions.
  * **`$top`** & **`$skip`**: Limit and offset for simple client-side pagination.
  * **`$skiptoken`**: Robust server-side, token-based pagination with automatic `@odata.nextLink` generation.
  * **`$count`**: Requests a total count of matching entities instead of returning the data.
  * **`$search`**: Full-text search across one or more pre-configured model fields.

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
  * **High-Performance Eager Loading**: Automatically resolves the **N+1 query problem** using Peewee's `prefetch`, ensuring that even complex `$expand` operations are executed in a minimal number of database queries.
  * **Optimistic Concurrency Control**: Supports **ETag** generation (`@odata.etag`) for safe concurrent updates.
  * **Flexible Key Management**: Natively handles entity lookups by primary key, composite keys, or any designated **unique field** (e.g., `/Users(email='jane@example.com')`).
  * **Relationship Navigation**: Seamlessly traverses foreign keys and back-references in URL paths (e.g., `/Users(123)/Orders`).
  * **Automatic Relationship Expansion**: Optionally configure the API to expand all direct foreign key relationships by default, without requiring an explicit `$expand` clause.
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

# In-memory SQLite database for the example
db = SqliteDatabase(':memory:')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    id = AutoField()
    name = CharField()
    email = CharField(unique=True)
    age = IntegerField()
    is_active = BooleanField(default=True)
    created_date = DateTimeField(default=datetime.datetime.now)

class Order(BaseModel):
    id = AutoField()
    user = ForeignKeyField(User, backref='orders')
    product = CharField()
    amount = DecimalField()
    created_date = DateTimeField(default=datetime.datetime.now)

# List of models exposed through the OData API
MODELS = [User, Order]

# Create tables
db.connect()
db.create_tables(MODELS)
```

### 2\. Perform Queries

```python
# Basic GET request for a collection
url = "/users"
query = PeeweeODataQuery(MODELS, url)
results = query.to_odata_response(query.query())

# Access a user by their primary key: /users(123)
query_by_id = PeeweeODataQuery(MODELS, "/users(123)")
user = query_by_id.to_odata_response(query_by_id.query())

# Access by a unique field: /users(email='john@example.com')
query_by_email = PeeweeODataQuery(MODELS, "/users(email='john@example.com')")
# Designate 'email' as the lookup key for the User model
query_by_email.set_model_ufield_as_key(User, 'email')
user = query_by_email.to_odata_response(query_by_email.query())
```

-----

## 💡 Advanced Query Examples

Here are examples of how to use various OData query options.

### `$select`: Specifying Fields

To limit the properties returned, use `$select`.

```python
# GET /users?$select=name,email
# Returns a list of users, but only with their 'name' and 'email' fields.
url = "/users?$select=name,email"
query = PeeweeODataQuery(MODELS, url)
results = query.to_odata_response(query.query())
```

### `$expand`: Including Related Data

To load related entities, use `$expand`. This operation is highly optimized to prevent performance bottlenecks.

```python
# GET /users?$select=name&$expand=orders($filter=amount gt 100;$select=product,amount)
# Returns users' names and, for each user, embeds a list of their orders
# where the amount is over 100, showing only the product and amount of each order.
url = "/users?$select=name&$expand=orders($filter=amount gt 100;$select=product,amount)"
query = PeeweeODataQuery(MODELS, url, expandable=[Order])
results = query.to_odata_response(query.query())
```

**Note**: OData uses `&` as a separator, but for nested queries inside parentheses, this library also correctly parses `;` as a separator to simplify URL encoding.

### `$orderby`: Sorting Results

Sort by one or more fields in `asc` (default) or `desc` order.

```python
# GET /orders?$orderby=amount desc,created_date
# Returns all orders, sorted first by amount descending, then by creation date ascending.
url = "/orders?$orderby=amount desc,created_date"
query = PeeweeODataQuery(MODELS, url)
results = query.to_odata_response(query.query())
```

### `$count`: Getting a Total Count

To get only the number of items that match a query, set `$count=true`.

```python
# GET /users?$filter=is_active eq true&$count=true
# Returns an integer representing the total count of active users.
url = "/users?$filter=is_active eq true&$count=true"
query = PeeweeODataQuery(MODELS, url)
count = query.to_odata_response(query.query()) # Returns "5" instead of a JSON object
```

### `$search`: Full-Text Search

First, configure which fields are searchable for a model.

```python
# GET /users?$search="jane"
# Searches for "jane" within the 'name' and 'email' fields.
url = "/users?$search=\"jane\""
query = PeeweeODataQuery(MODELS, url)
query.set_search_fields(['name', 'email']) # Configure searchable fields
results = query.to_odata_response(query.query())
```

### Navigating to Related Entities

You can directly query a related collection or entity through URL path navigation.

```python
# GET /users(123)/orders?$filter=amount gt 50
# Directly retrieves all orders for user 123 where the amount is greater than 50.
url = "/users(123)/orders?$filter=amount gt 50"
query = PeeweeODataQuery(MODELS, url)
orders = query.to_odata_response(query.query())
```

-----

## 🔨 CRUD Operations

### Create (POST)

```python
# POST /users
query = PeeweeODataQuery(MODELS, "/users")
new_user_data = {'name': 'Jane Doe', 'email': 'jane@example.com', 'age': 30}
new_user = query.create(new_user_data)
```

### Update (PUT / PATCH)

Use `patch=True` for partial updates. `patch=False` (or omitted) requires all fields for a full replacement (PUT).

```python
# PATCH /users(123)
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

### General Configuration

```python
query = PeeweeODataQuery(MODELS, "/users?$top=5")

# Enable server-side pagination with a page size of 100.
# This will automatically add '@odata.nextLink' to results.
query.set_skiptoken(100)

# Hide sensitive fields like a password hash from all outputs.
query.set_hidden_fields(['password_hash'])

# Configure searchable fields for the $search operator.
query.set_search_fields(['name', 'email'])

# Set a max recursion depth for $expand to prevent overly complex queries.
query.set_max_expand(3)

# Add global 'where' conditions for a model (e.g., for tenancy or soft-delete).
# This condition will be AND-ed with all other filters for the User model.
query.add_restricition(User, [User.is_active == True])

# Automatically expand all direct foreign key relationships in the output JSON.
# For example, a query to /orders will automatically include the full user object.
query.set_expand_complex(True)
```

### Response Metadata Configuration (`@odata.id` and `@odata.etag`)

You can control the OData metadata fields included in the JSON response.

**ETags (`@odata.etag`)** are used for optimistic concurrency control. To enable them, you must provide a method on your Peewee model that generates the ETag value.

```python
# 1. First, add an ETag generation method to your model.
#    A last-updated timestamp or a version number are good sources.
class User(BaseModel):
    # ... other fields
    updated_at = DateTimeField(default=datetime.datetime.now)

    def get_etag(self):
        # Generate a weak ETag from the timestamp
        return f'W/"{self.updated_at.timestamp()}"'

# 2. Instantiate the query engine, providing the NAME of the ETag method.
query = PeeweeODataQuery(MODELS, "/users(1)", etag_callable='get_etag')

# 3. Enable ETag inclusion in the response.
query.include_etag = True

# The resulting JSON will include: "@odata.etag": "W/\"1754321098.76543\""
user = query.to_odata_response(query.query())
```

**Entity IDs (`@odata.id`)** provide the canonical URL for each entity in the response. They are enabled by default.

```python
# By default, with_odata_id is True.
query = PeeweeODataQuery(MODELS, "/users")
# The response will include: "@odata.id": "users(1)"

# You can disable this behavior if not needed.
query.with_odata_id = False
```

-----

## 🏗️ Architecture & Parser Details

The library's power comes from its two-layer architecture: the parser and the query engine.

### Core Components

  * **`ODataURLParser`**: A utility that intelligently splits OData query strings, properly handling nested parentheses and quotes found in complex `$expand` and `$filter` clauses.
  * **`ODataParser`**: The primary parser that uses the **Lark** library with a formal OData grammar to transform a URL into a structured Python object tree.
  * **`PeeweeODataQuery`**: The main engine that consumes the object tree from the parser and builds the corresponding Peewee ORM query.

### Understanding the `$filter` Expression Tree

When `ODataParser` processes a `$filter` string, it transforms it into a nested object structure—an **expression tree**. This tree is then easy for the `PeeweeODataQuery` engine to traverse and convert into a database query.

The tree is composed of the following object types:

  * `ODataLogOperator`: Represents a logical operation: `and`, `or`, `not`.
  * `ODataOperator`: Represents a comparison (`eq`, `ne`, `gt`) or arithmetic (`add`, `sub`) operation.
  * `ODataFunction`: Represents a function call like `contains()` or `now()`.
  * `ODataField`: A leaf node representing a model's field (e.g., `name`).
  * `ODataPrimitve`: A leaf node representing a literal value (e.g., the string `'John'` or the number `25`).

#### Example Breakdown

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

The `PeeweeODataQuery` engine recursively traverses this tree to build the final Peewee expression: `((User.age > 25) & (User.name.contains('John'))) | (User.email.startswith('admin'))`.

-----

## 🚨 Limitations

  * **Deep Structure Mutations**: Complex nested create/update operations in a single request (deep inserts) are not yet supported.
  * **Advanced OData Functions**: Some OData v4 functions beyond string, date, and arithmetic operations are not implemented.
  * **Performance**: While the library is optimized to prevent N+1 query problems using `prefetch`, extremely complex queries on very large datasets still benefit from proper database indexing.

-----

## 🤝 Contributing & Support

  * **Issues**: GitHub issue tracker
  * **Email**: lmartynov@tuta.com
  * **Documentation**: See inline code documentation for detailed API reference.
