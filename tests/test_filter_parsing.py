import pytest
from lark import Lark
from odata.filter import ODataFilterTransformer, ODataFunction, odata_filter_grammar

class TestFilterParsing:
    """Test OData filter parsing functionality in isolation"""
    
    @pytest.fixture
    def parser(self):
        """Create filter parser instance"""
        return Lark(odata_filter_grammar, parser='lalr', transformer=ODataFilterTransformer())
    
    def test_simple_eq_filter(self, parser):
        """Test simple equality filter"""
        result = parser.parse("name eq 'John'")
        print(result)
        assert result.a.name == "name"
        assert result.name == "eq"
        assert result.b.value == "John"
    
    def test_numeric_comparison(self, parser):
        """Test numeric comparisons"""
        test_cases = [
            ("age gt 25", "gt", 25.0),
            ("price lt 100.5", "lt", 100.5),
            ("count ge 10", "ge", 10.0),
            ("rating le 4.5", "le", 4.5),
            ("id ne 0", "ne", 0.0)
        ]
        
        for filter_expr, expected_op, expected_value in test_cases:
            result = parser.parse(filter_expr)
            assert result.name == expected_op
            assert result.b.value == expected_value
    
    def test_boolean_values(self, parser):
        """Test boolean value parsing"""
        true_result = parser.parse("is_active eq true")
        false_result = parser.parse("is_deleted eq false")
        
        assert true_result.b.value is True
        assert false_result.b.value is False
    
    def test_null_value(self, parser):
        """Test null value parsing"""
        result = parser.parse("description eq null")
        assert result.b.value is None
    
    def test_string_functions(self, parser):
        """Test string functions"""
        test_cases = [
            "contains(name,'John')",
            "startswith(email,'admin')",
            "endswith(filename,'.pdf')"
        ]
        
        for filter_expr in test_cases:
            result = parser.parse(filter_expr)
            assert type(result) == ODataFunction
            assert result.args
            assert len(result.args) == 2
    
    def test_and_expression(self, parser):
        """Test AND logical expression"""
        result = parser.parse("(9 add 9) gt age and is_active eq true")
        
        assert result.name == "and"

        first = result.left
        # First condition
        assert first.a.a.value == 9 
        assert first.name == "gt"
        assert first.b.name == "age"
        
        # Second condition
        second = result.right
        assert second.a.name == "is_active"
        assert second.name == "eq"
        assert second.b.value is True
    
    def test_or_expression(self, parser):
        """Test OR logical expression"""
        result = parser.parse("status eq 'active' or status eq 'pending'")
        
        assert result.name == "or"
        assert result.left.name == "eq"
        assert result.right.name == "eq"
        
    
    def test_not_expression(self, parser):
        """Test NOT logical expression"""
        result = parser.parse("not is_deleted eq true")
        
        assert result.name == "not"
        inner = result.right
        assert inner.a.name == "is_deleted"
        assert inner.name == "eq"
        assert inner.b.value is True
    
    def test_complex_expression(self, parser):
        """Test complex nested expressions"""
        result = parser.parse("(age gt 18 and age lt 65) or is_vip eq true")
        
        assert result.name == "or"
        
        # Left side should be an AND expression
        left = result.left.name
        assert "and" == left
        
        # Right side should be simple comparison
        right = result.right.a.name
        assert right == "is_vip"
    
    def test_path_expressions(self, parser):
        """Test nested field paths"""
        result = parser.parse("user/name eq 'John'")
        
        assert result.a.name == "user/name"
        assert result.name == "eq"
        assert result.b.value == "John"
    
    def test_single_quoted_strings(self, parser):
        """Test single-quoted string values"""
        result = parser.parse("name eq 'John O''Brian'")
        
        assert result.a.name == "name"
        assert result.b.value == "John O'Brian"
    
    def test_double_quoted_strings(self, parser):
        """Test double-quoted string values"""
        result = parser.parse('description eq "Product with \\"quotes\\""')
        
        assert result.a.name == "description"
        assert result.b.value == 'Product with "quotes"'
    
    def test_function_with_multiple_args(self, parser):
        """Test functions with multiple arguments"""
        # Note: This test depends on your grammar supporting multi-arg functions
        # Adjust based on your actual implementation
        result = parser.parse("contains(description,'test')")
        
        assert result.name == "contains"
        assert len(result.args) == 2
        assert result.args[0].name == "description"
        assert result.args[1].value == "test"
    
    def test_precedence(self, parser):
        """Test operator precedence"""
        # AND should bind tighter than OR
        result = parser.parse("a eq 1 or b eq 2 and c eq 3")
        
        assert result.name == "or"
        # The AND should be on the right side due to precedence
        right_side = result.right
        assert right_side.name == "and"
    def test_complex(self,parser):
        """Test complex filter"""
        result = parser.parse("not(contains(Person/email,'x')) and ( created_at gt '2025-08-01T10:10:57' or startswith(name,'hello') )")

    def test_errors(self,parser):
        """Test complex filter"""
        error = False
        try:
            result = parser.parse("not(contains(Person/email,'x')) and ( created_at gt eq '2025-08-01T10:10:57' or startswith(name,'hello') )")
        except:
            error = True
        assert error == True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
