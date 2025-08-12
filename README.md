# OData Peewee Integration

A comprehensive Python library that provides OData v4 query parsing and seamless integration with Peewee ORM, enabling RESTful API endpoints with full OData query capabilities.

## 🚀 Features

### Complete OData v4 Query Support

- **$filter** - Advanced filtering with Boolean conditions and logical operators (AND/OR/NOT)
- **$select** - Field selection with comma-separated lists
- **$expand** - Include related entities inline with support for nested parameters and sub-queries
- **$orderby** - Multi-field sorting with ascending/descending directions
- **$top** - Result limiting for pagination
- **$skip** - Offset-based pagination
- **$skiptoken** - Server-side pagination with automatic next-link generation
- **$count** - Entity count requests
- **$search** - Full-text search across specified fields
- **$format** - Response media type specification (parser support)

### Advanced Filtering Capabilities

- **Comparison operators**: `eq`, `ne`, `gt`, `lt`, `ge`, `le`
- **String functions**: `contains()`, `startswith()`, `endswith()`
- **Logical operators**: `and`, `or`, `not`
- **Complex nested expressions** with parentheses
- **Field navigation** through relationships (e.g., `order/customer/name`)

### Full CRUD Operations

- **GET** - Query entities with complete OData parameter support
- **POST** - Create new entities with relationship handling
- **PUT/PATCH** - Update existing entities (full or partial updates)
- **DELETE** - Remove entities with proper validation

### Enterprise-Ready Features

- **Relationship Navigation** - Foreign keys and backref traversal
- **Circular Reference Protection** - Automatic detection and prevention
- **Access Control** - Model-level permissions for browsing, modification, and expansion
- **Comprehensive Logging** - Full operation tracking and debugging
- **ETag Support** - Optimistic concurrency control
- **OData Metadata** - Automatic CSDL/XML metadata generation
- **Hidden Fields** - Security through field visibility control
- **Search Integration** - Configurable full-text search across model fields

## 📦 Installation

```bash
pip install peewee lark
```

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

## 🏗️ Architecture

### Core Components

- **ODataParser** - Robust URL and query parameter parsing using Lark grammar
- **PeeweeODataQuery** - Main query execution engine with relationship handling
- **NavigationPath** - Path resolution and relationship traversal
- **PeeweeODataMeta** - Automatic OData metadata generation

### Query Processing Pipeline

1. **URL Parsing** - Extract OData parameters and navigation paths
2. **Model Resolution** - Resolve entity types and relationships
3. **Security Validation** - Apply access controls and permissions
4. **Query Construction** - Build Peewee queries with joins and filters
5. **Result Processing** - Format results with OData conventions
6. **Response Generation** - Include metadata, etags, and pagination links

## 📊 Advanced Examples

### Complex Filtering

```python
# Multiple conditions with grouping
url = "/users?$filter=(age gt 18 and age lt 65) and (contains(name,'John') or contains(email,'john'))"

# Date-based filtering
url = "/orders?$filter=created_date ge 2023-01-01T00:00:00Z and amount gt 100"

# Relationship filtering
url = "/users?$filter=orders/any(o: o/amount gt 1000)"
```

### Multi-Level Expansion

```python
# Deep relationship expansion
url = "/users?$expand=orders($expand=items($select=name,price;$orderby=price desc))"

# Conditional expansion
url = "/customers?$expand=orders($filter=status eq 'active';$expand=items)"
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

## ⚙️ Configuration Options

### Constructor Parameters

- **models** - Primary models that can be browsed and modified
- **expandable** - Models that can only be expanded (read-only)
- **logger** - Logger instance for operation tracking
- **etag_callable** - Method to generate ETags for concurrency control
- **select_always** - Fields always included in queries (e.g., 'id', 'modified_date')

### Runtime Configuration

```python
query.set_expand_complex(False)  # Disable automatic FK expansion
query.add_restriction(User, [User.active == True])  # Add model-level filters
```

## 🚨 Current Limitations

- **Single Primary Key** - Only supports models with single-column primary keys
- **Deep Structure Operations** - Complex nested create/update operations not yet supported
- **Advanced OData Functions** - Some OData v4 functions are not implemented
- **Performance** - Complex nested expansions may require optimization for large datasets

## 🤝 Contributing

We welcome contributions! Please ensure:

1. **Code Quality** - Follow existing patterns and add comprehensive tests
2. **Documentation** - Update README and inline documentation
3. **Performance** - Consider performance implications of changes
4. **Backward Compatibility** - Maintain API compatibility where possible

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

- **Issues**: GitHub issue tracker
- **Email**: lmartynov@tuta.com
- **Documentation**: See inline code documentation for detailed API reference

---

**Built with ❤️ for the Python community**
