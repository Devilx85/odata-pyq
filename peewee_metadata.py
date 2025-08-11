import xml.etree.ElementTree as ET
from xml.dom import minidom
from peewee import *
from typing import Set, Optional, Union, List
import inspect

class PeeweeODataMeta:
    def peewee_to_odata_type(field_type):
        """Convert Peewee field types to OData EDM types."""
        type_mapping = {
            CharField: 'Edm.String',
            TextField: 'Edm.String',
            IntegerField: 'Edm.Int32',
            BigIntegerField: 'Edm.Int64',
            SmallIntegerField: 'Edm.Int16',
            FloatField: 'Edm.Double',
            DoubleField: 'Edm.Double',
            DecimalField: 'Edm.Decimal',
            BooleanField: 'Edm.Boolean',
            DateField: 'Edm.Date',
            DateTimeField: 'Edm.DateTimeOffset',
            TimeField: 'Edm.TimeOfDay',
            TimestampField: 'Edm.DateTimeOffset',
            BlobField: 'Edm.Binary',
            UUIDField: 'Edm.Guid',
            ForeignKeyField: 'Edm.Int32',  # Default, will be overridden by related field type
        }
        
        return type_mapping.get(type(field_type), 'Edm.String')


    def is_nullable_field(field):
        """Check if a field is nullable."""
        return field.null or isinstance(field, ForeignKeyField)


    def get_max_length(field):
        """Get max length for string fields."""
        if hasattr(field, 'max_length') and field.max_length:
            return str(field.max_length)
        return None


    def find_backreferences(model_class, all_models=None):
        """
        Find backreferences by examining foreign key relationships.
        This is more reliable than relying on _meta.backrefs structure.
        """
        backrefs = []
        
        if all_models is None:
            # Try to get all models from the database registry
            try:
                all_models = list(model_class._meta.database._models.values())
            except:
                # If that fails, we can't find backrefs without explicit model list
                return backrefs
        
        # Look through all models to find those that reference this model
        for other_model in all_models:
            if other_model == model_class:
                continue
                
            # Check each field in the other model
            for field_name, field_obj in other_model._meta.fields.items():
                if isinstance(field_obj, ForeignKeyField) and field_obj.rel_model == model_class:
                    # Found a backref - the field name becomes the collection name
                    backref_name = getattr(field_obj, 'backref', f"{other_model.__name__.lower()}s")
                    backrefs.append({
                        'name': backref_name,
                        'related_model': other_model,
                        'foreign_key_field': field_name
                    })
        
        return backrefs


    # Example usage and helper function to create metadata for multiple models
    def create_multi_model_metadata(
        model_classes: List,
        namespace: str = "DefaultNamespace",
        container_name: str = "DefaultContainer",
        field_configs: Optional[dict] = None,
        include_navigation: bool = True
    ):
        """
        Create OData v4 metadata document for multiple Peewee model classes.
        
        Args:
            model_classes: List of Peewee model classes
            namespace: OData namespace
            container_name: OData container name
            field_configs: Dict with model names as keys and field config as values
                        e.g., {'User': {'allowed_fields': ['id', 'name']}}
            include_navigation: Whether to include navigation properties
        
        Returns:
            str: Formatted XML metadata document
        """
        if field_configs is None:
            field_configs = {}
        
        # Create root element
        root = ET.Element('edmx:Edmx')
        root.set('xmlns:edmx', 'http://docs.oasis-open.org/odata/ns/edmx')
        root.set('Version', '4.0')
        
        # Create DataServices element
        data_services = ET.SubElement(root, 'edmx:DataServices')
        
        # Create Schema element
        schema = ET.SubElement(data_services, 'Schema')
        schema.set('xmlns', 'http://docs.oasis-open.org/odata/ns/edm')
        schema.set('Namespace', namespace)
        
        # Create EntityContainer
        container = ET.SubElement(schema, 'EntityContainer')
        container.set('Name', container_name)
        
        # Process each model
        for model_class in model_classes:
            model_name = model_class.__name__
            config = field_configs.get(model_name, {})
            
            # Create EntityType (reuse logic from single model function)
            entity_type = ET.SubElement(schema, 'EntityType')
            entity_type.set('Name', model_name)
            
            # Find primary key
            primary_key_field = None
            for field_name, field_obj in model_class._meta.fields.items():
                if field_obj.primary_key:
                    primary_key_field = field_name
                    break
            
            # Create Key element
            if primary_key_field:
                key_element = ET.SubElement(entity_type, 'Key')
                property_ref = ET.SubElement(key_element, 'PropertyRef')
                property_ref.set('Name', primary_key_field)
            
            # Get field configuration
            allowed_fields = config.get('allowed_fields')
            excluded_fields = config.get('excluded_fields')
            
            # Convert to sets if needed
            if allowed_fields is not None:
                allowed_fields = set(allowed_fields) if not isinstance(allowed_fields, set) else allowed_fields
            if excluded_fields is not None:
                excluded_fields = set(excluded_fields) if not isinstance(excluded_fields, set) else excluded_fields
            
            # Track navigation properties
            navigation_properties = []
            
            # Process fields (same logic as single model)
            for field_name, field_obj in model_class._meta.fields.items():
                # Apply field filtering
                if allowed_fields is not None and field_name not in allowed_fields:
                    continue
                if excluded_fields is not None and field_name in excluded_fields:
                    continue
                
                if isinstance(field_obj, ForeignKeyField):
                    if include_navigation:
                        nav_prop = {
                            'name': field_name,
                            'type': f"{namespace}.{field_obj.rel_model.__name__}",
                            'nullable': PeeweeODataMeta.is_nullable_field(field_obj),
                            'is_collection': False
                        }
                        navigation_properties.append(nav_prop)
                    
                    # Foreign key property
                    fk_property = ET.SubElement(entity_type, 'Property')
                    fk_property.set('Name', f"{field_name}Id")
                    
                    related_pk_type = 'Edm.Int32'
                    if hasattr(field_obj.rel_model._meta, 'primary_key'):
                        related_pk_field = field_obj.rel_model._meta.primary_key
                        related_pk_type = PeeweeODataMeta.peewee_to_odata_type(related_pk_field)
                    
                    fk_property.set('Type', related_pk_type)
                    fk_property.set('Nullable', str(PeeweeODataMeta.is_nullable_field(field_obj)).lower())
                
                else:
                    # Regular property
                    property_elem = ET.SubElement(entity_type, 'Property')
                    property_elem.set('Name', field_name)
                    property_elem.set('Type', PeeweeODataMeta.peewee_to_odata_type(field_obj))
                    property_elem.set('Nullable', str(PeeweeODataMeta.is_nullable_field(field_obj)).lower())
                    
                    max_length = PeeweeODataMeta.get_max_length(field_obj)
                    if max_length:
                        property_elem.set('MaxLength', max_length)
            
            # Add backreference navigation properties - use more reliable method
            if include_navigation:
                try:
                    backrefs = PeeweeODataMeta.find_backreferences(model_class, model_classes)
                    for backref in backrefs:
                        backref_name = backref['name']
                        
                        # Apply field filtering
                        if allowed_fields is not None and backref_name not in allowed_fields:
                            continue
                        if excluded_fields is not None and backref_name in excluded_fields:
                            continue
                        
                        # Check if we haven't already added this navigation property
                        if not any(nav['name'] == backref_name for nav in navigation_properties):
                            nav_prop = {
                                'name': backref_name,
                                'type': f"Collection({namespace}.{backref['related_model'].__name__})",
                                'nullable': False,
                                'is_collection': True
                            }
                            navigation_properties.append(nav_prop)
                except:
                    pass
            
            # Create navigation property elements
            for nav_prop in navigation_properties:
                nav_element = ET.SubElement(entity_type, 'NavigationProperty')
                nav_element.set('Name', nav_prop['name'])
                nav_element.set('Type', nav_prop['type'])
                if nav_prop['nullable']:
                    nav_element.set('Nullable', 'true')
            
            # Create EntitySet
            entity_set = ET.SubElement(container, 'EntitySet')
            entity_set.set('Name', f"{model_name}s")
            entity_set.set('EntityType', f"{namespace}.{model_name}")
        
        # Convert to pretty-printed string
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent='  ')
        
        # Remove empty lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        return '\n'.join(lines)


