import pytest
import tempfile
import os
from datetime import datetime, date
from peewee import *
from unittest.mock import Mock

from odata.filter import ODataLogOperator, ODataOperator

# Assuming your package structure - adjust imports as needed
from odata.odata_parser import ODataParser
from odata.peewee_qodata import PeeweeODataQuery, DataType
from odata.peewee_metadata import PeeweeODataMeta

# Test database setup
test_db = SqliteDatabase(':memory:')

# Test models
class User(Model):
    id = AutoField()
    name = CharField(max_length=100)
    email = CharField(max_length=200)
    age = IntegerField(null=True)
    is_active = BooleanField(default=True)
    created_date = DateTimeField(default=datetime.now)
    birth_date = DateField(null=True)
    
    class Meta:
        database = test_db

class Order(Model):
    id = AutoField()
    user = ForeignKeyField(User, backref='orders')
    total = FloatField()
    order_date = DateTimeField(default=datetime.now)
    description = TextField(null=True)
    is_shipped = BooleanField(default=False)
    
    class Meta:
        database = test_db

class Product(Model):
    id = AutoField()
    name = CharField(max_length=100)
    price = FloatField()
    category = CharField(max_length=50, null=True)
    in_stock = BooleanField(default=True)
    
    class Meta:
        database = test_db

class OrderItem(Model):
    id = AutoField()
    order = ForeignKeyField(Order, backref='items')
    product = ForeignKeyField(Product, backref='order_items')
    quantity = IntegerField()
    unit_price = FloatField()
    
    class Meta:
        database = test_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Setup test database and create tables"""
    test_db.connect()
    test_db.create_tables([User, Order, Product, OrderItem])
    
    # Create test data
    user1 = User.create(
        name="John Doe", 
        email="john@example.com", 
        age=30,
        birth_date=date(1993, 5, 15)
    )
    user2 = User.create(
        name="Jane Smith", 
        email="jane@example.com", 
        age=25,
        birth_date=date(1998, 8, 22)
    )
    user3 = User.create(
        name="Bob Wilson", 
        email="bob@example.com", 
        age=35,
        is_active=False,
        birth_date=date(1988, 12, 3)
    )
    
    product1 = Product.create(name="Laptop", price=999.99, category="Electronics")
    product2 = Product.create(name="Mouse", price=29.99, category="Electronics")
    product3 = Product.create(name="Keyboard", price=79.99, category="Electronics", in_stock=False)
    
    order1 = Order.create(user=user1, total=1099.98, description="First order")
    order2 = Order.create(user=user1, total=79.99, description="Second order", is_shipped=True)
    order3 = Order.create(user=user2, total=29.99, description="Jane's order")
    
    OrderItem.create(order=order1, product=product1, quantity=1, unit_price=999.99)
    OrderItem.create(order=order1, product=product2, quantity=1, unit_price=29.99)
    OrderItem.create(order=order2, product=product3, quantity=1, unit_price=79.99)
    OrderItem.create(order=order3, product=product2, quantity=1, unit_price=29.99)
    
    yield
    
    test_db.drop_tables([User, Order, Product, OrderItem])
    test_db.close()

class TestODataURLParser:
    """Test OData URL parsing functionality"""
    
    def test_basic_url_parsing(self):
        """Test basic URL parsing without query parameters"""
        parser = ODataParser("/users")
        parser.run()
        
        assert parser.parsed_path[0]["entity"] == "users"
        assert parser.parsed_path[0]["keys"] is None
    
    def test_url_with_id(self):
        """Test URL parsing with entity ID"""
        parser = ODataParser("http://localhost/api/users(123)")
        parser.run()
        
        assert parser.parsed_path[1]["entity"] == "users"
        assert parser.parsed_path[1]["keys"] == [123]
    
    def test_navigation_path(self):
        """Test URL parsing with navigation paths"""
        parser = ODataParser("http://localhost/api/users(123)/orders")
        parser.run()
        
        assert len(parser.parsed_path) == 3
        assert parser.parsed_path[1]["entity"] == "users"
        assert parser.parsed_path[1]["keys"] == [123]
        assert parser.parsed_path[2]["entity"] == "orders"
        assert parser.parsed_path[2]["keys"] is None
    
    def test_filter_parsing(self):
        """Test $filter parameter parsing"""
        parser = ODataParser("http://localhost/api/users?$filter=age gt 25")
        parser.run()
        
        assert parser.filter is not None
        assert type(parser.filter) == ODataOperator
        assert parser.filter.a.name == "age"
        assert parser.filter.name == "gt"
        assert parser.filter.b.value == 25
    
    def test_complex_filter_parsing(self):
        """Test complex $filter with AND/OR"""
        parser = ODataParser("http://localhost/api/users?$filter=age gt 25 and name eq 'John'")
        parser.run()
        
        assert parser.filter is not None
        assert type(parser.filter) == ODataLogOperator

    
    def test_select_parsing(self):
        """Test $select parameter parsing"""
        parser = ODataParser("http://localhost/api/users?$select=id,name,email")
        parser.run()
        
        assert parser.select == ["id", "name", "email"]
    
    def test_orderby_parsing(self):
        """Test $orderby parameter parsing"""
        parser = ODataParser("http://localhost/api/users?$orderby=name asc,age desc")
        parser.run()
        
        assert parser.orderby is not None
        assert parser.orderby["name"] == "asc"
        assert parser.orderby["age"] == "desc"
    
    def test_expand_parsing(self):
        """Test $expand parameter parsing"""
        parser = ODataParser("http://localhost/api/users?$expand=orders($select=id;$filter=id gt 5)")
        parser.run()
        
        assert parser.expand[0][1] == "$select=id;$filter=id gt 5"
        assert len(parser.expand) == 1
        assert parser.expand[0][0] == "orders"
    
    def test_pagination_params(self):
        """Test $top and $skip parameters"""
        parser = ODataParser("http://localhost/api/users?$top=10&$skip=20")
        parser.run()
        
        assert parser.top == 10
        assert parser.skip == 20
    
    def test_count_param(self):
        """Test $count parameter"""
        parser = ODataParser("http://localhost/api/users?$count=true")
        parser.run()
        
        assert parser.count is True
    
    def test_search_param(self):
        """Test $search parameter"""
        parser = ODataParser("http://localhost/api/users?$search=john")
        parser.run()
        
        assert parser.search == "john"
    def test_complex_request(self):
        """Test several parameters together"""
        parser = ODataParser("http://localhost/api/?$filter=users/id gt 7&$expand=users($select=id,email;$filter=not(contains(email,'x')) and created_at gt '2025-08-01T10:10:57';$orderby=id desc)&$top=1&$skip=0")
        parser.run()

class TestPeeweeODataQuery:
    """Test Peewee OData integration"""
    
    def test_basic_query(self):
        """Test basic entity collection query"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users")
        result = query_obj.query()
        
        assert query_obj.navigated_class == User
        assert len(list(result)) == 3  # We created 3 users
    
    def test_single_entity_query(self):
        """Test single entity query with ID"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users(1)")
        result = list(query_obj.query())
        
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].name == "John Doe"
    
    def test_filter_query(self):
        """Test query with $filter"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users?$filter=30 lt age")
        result = list(query_obj.query())
        
        assert len(result) == 1
        assert result[0].name == "Bob Wilson"
        assert result[0].age == 35
    
    def test_filter_string_contains(self):
        """Test string contains filter"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users?$filter=contains(name,'John')")
        result = list(query_obj.query())
        
        assert len(result) == 1
        assert result[0].name == "John Doe"
    
    def test_filter_boolean(self):
        """Test boolean filter"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users?$filter=is_active eq false")
        result = list(query_obj.query())
        
        assert len(result) == 1
        assert result[0].name == "Bob Wilson"
        assert result[0].is_active is False
    
    def test_complex_filter(self):
        """Test complex filter with AND"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users?$filter=age gt 25 and is_active eq true")
        result = list(query_obj.query())
        
        assert len(result) == 1
        assert result[0].name == "John Doe"
    
    def test_orderby_query(self):
        """Test query with $orderby"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users?$orderby=age desc")
        result = list(query_obj.query())
        
        ages = [user.age for user in result]
        assert ages == [35, 30, 25]  # Descending order
    
    def test_select_query(self):
        """Test query with $select"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users?$select=id,name")
        result = list(query_obj.query())
        
        # The query should still return full objects but track selected fields
        assert len(result) == 3
        assert list(result[0].__data__.keys()) == ["id", "name"]
    
    def test_top_skip_query(self):
        """Test query with $top and $skip"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users?$orderby=id&$top=2&$skip=1")
        result = list(query_obj.query())
        
        assert len(result) == 2
        assert result[0].id == 2  # Second user (after skip=1)
        assert result[1].id == 3  # Third user
    
    def test_count_query(self):
        """Test query with $count"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users?$count=true")
        result = query_obj.query()
        
        assert result == 3  # Count of users
    
    def test_navigation_query(self):
        """Test navigation to related entities"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users(1)/orders")
        result = list(query_obj.query())
        
        assert query_obj.navigated_class == Order
        assert len(result) == 2  # User 1 has 2 orders
        assert all(order.user_id == 1 for order in result)
    
    def test_expand_query(self):
        """Test query with $expand"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users?$expand=orders")
        result = list(query_obj.query())
        
        assert len(result) == 3
        assert len(query_obj.expands) == 1
        assert query_obj.expands[0][1] == "orders"  # expand field name
    
    def test_search_functionality(self):
        """Test search functionality"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users?$search=john")
        query_obj.set_search_fields(["name", "email"])
        result = list(query_obj.query())
        
        # Should find users with 'john' in name or email
        assert len(result) >= 1
    
    def test_create_entity(self):
        """Test entity creation"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users")
        
        new_user_data = {
            "name": "Test User",
            "email": "test@example.com",
            "age": 28
        }
        
        created_user = query_obj.create(new_user_data)
        
        assert created_user.name == "Test User"
        assert created_user.email == "test@example.com"
        assert created_user.age == 28
        
        # Clean up
        created_user.delete_instance()
    
    def test_update_entity(self):
        """Test entity update"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users(1)")
        
        update_data = {
            "name": "John Updated",
            "age": 31
        }
        
        updated_user = query_obj.update(update_data, patch=True)
        
        assert updated_user.name == "John Updated"
        assert updated_user.age == 31
        
        # Restore original data
        restore_data = {"name": "John Doe", "age": 30}
        query_obj.update(restore_data, patch=True)
    
    def test_delete_entity(self):
        """Test entity deletion"""
        models = [User, Order, Product, OrderItem]
        
        # First create a user to delete
        test_user = User.create(name="To Delete", email="delete@example.com", age=40)
        
        query_obj = PeeweeODataQuery(models, f"/users({test_user.id})")
        deleted_user = query_obj.delete()
        
        assert deleted_user.name == "To Delete"
        
        # Verify user is deleted
        with pytest.raises(User.DoesNotExist):
            User.get_by_id(test_user.id)
    
    def test_to_odata_response(self):
        """Test OData response serialization"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users")
        result = list(query_obj.query())
        
        odata_response = query_obj.to_odata_response(result)
        
        assert "value" in odata_response
        assert len(odata_response["value"]) == 3
        
        # Check first user data
        first_user = odata_response["value"][0]
        assert "id" in first_user
        assert "name" in first_user
        assert "email" in first_user
        assert "@odata.id" in first_user
    
    def test_restrictions(self):
        """Test model restrictions"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users")
        
        # Add restriction to only show active users
        query_obj.add_restricition(User, [User.is_active == True])
        
        result = list(query_obj.query())
        
        # Should only return active users (2 out of 3)
        assert len(result) == 2
        assert all(user.is_active for user in result)
    
    def test_hidden_fields(self):
        """Test hidden fields functionality"""
        models = [User, Order, Product, OrderItem]
        query_obj = PeeweeODataQuery(models, "/users")
        query_obj.set_hidden_fields(["email"])
        
        result = list(query_obj.query())
        odata_response = query_obj.to_odata_response(result)
        
        # Email should be hidden (empty string)
        first_user = odata_response["value"][0]
        assert "email" not in first_user 

class TestPeeweeODataMeta:
    """Test metadata generation"""
    
    def test_peewee_to_odata_type_mapping(self):
        """Test field type mapping"""
        assert PeeweeODataMeta.peewee_to_odata_type(CharField()) == 'Edm.String'
        assert PeeweeODataMeta.peewee_to_odata_type(IntegerField()) == 'Edm.Int32'
        assert PeeweeODataMeta.peewee_to_odata_type(FloatField()) == 'Edm.Double'
        assert PeeweeODataMeta.peewee_to_odata_type(BooleanField()) == 'Edm.Boolean'
        assert PeeweeODataMeta.peewee_to_odata_type(DateField()) == 'Edm.Date'
        assert PeeweeODataMeta.peewee_to_odata_type(DateTimeField()) == 'Edm.DateTimeOffset'
    
    def test_nullable_field_detection(self):
        """Test nullable field detection"""
        nullable_field = CharField(null=True)
        non_nullable_field = CharField(null=False)
        fk_field = ForeignKeyField(User)
        
        assert PeeweeODataMeta.is_nullable_field(nullable_field) is True
        assert PeeweeODataMeta.is_nullable_field(non_nullable_field) is False
        assert PeeweeODataMeta.is_nullable_field(fk_field) is True
    
    def test_max_length_detection(self):
        """Test max length detection"""
        field_with_length = CharField(max_length=100)
        field_without_length = TextField()
        
        assert PeeweeODataMeta.get_max_length(field_with_length) == "100"
        assert PeeweeODataMeta.get_max_length(field_without_length) is None
    
    def test_metadata_generation(self):
        """Test XML metadata generation"""
        models = [User, Order, Product, OrderItem]
        metadata_xml = PeeweeODataMeta.create_multi_model_metadata(
            models,
            namespace="TestNamespace",
            container_name="TestContainer"
        )
        
        # Basic XML structure checks
        assert "<?xml" in metadata_xml
        assert "TestNamespace" in metadata_xml
        assert "TestContainer" in metadata_xml
        assert "EntityType" in metadata_xml
        assert "EntitySet" in metadata_xml
        
        # Check that all models are included
        for model in models:
            assert model.__name__ in metadata_xml

class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_invalid_entity_collection(self):
        """Test error when requesting non-existent entity collection"""
        models = [User]
        
        with pytest.raises(Exception) as exc_info:
            query_obj = PeeweeODataQuery(models, "/nonexistent")
        
        assert "does not exist" in str(exc_info.value)
    
    def test_invalid_filter_field(self):
        """Test error when filtering on non-existent field"""
        models = [User]
        
        with pytest.raises(Exception) as exc_info:
            query_obj = PeeweeODataQuery(models, "/users?$filter=nonexistent_field eq 'value'")
            list(query_obj.query())
        
        assert "Cannot find field" in str(exc_info.value)
    
    def test_unauthorized_model_access(self):
        """Test error when accessing unauthorized model"""
        models = [User]  # Only User is allowed
        
        with pytest.raises(Exception) as exc_info:
            query_obj = PeeweeODataQuery(models, "/orders")
        
        assert "does not exist" in str(exc_info.value)
    
    def test_create_with_query_params(self):
        """Test error when trying to create with query parameters"""
        models = [User]
        
        with pytest.raises(Exception) as exc_info:
            query_obj = PeeweeODataQuery(models, "/users?$filter=age gt 25")
            query_obj.create({"name": "Test"})
        
        assert "does not support query parameters" in str(exc_info.value)
    
    def test_update_collection(self):
        """Test error when trying to update a collection"""
        models = [User]
        
        with pytest.raises(Exception) as exc_info:
            query_obj = PeeweeODataQuery(models, "/users")
            query_obj.update({"name": "Test"})
        
        assert "Can only update entities" in str(exc_info.value)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
