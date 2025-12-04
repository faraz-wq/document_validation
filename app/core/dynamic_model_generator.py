from pydantic import BaseModel, Field, create_model
import json
from app.schemas.schema_models import FieldConfig, FieldType
from app.models import SourceDocument, BoundingBox  # Import existing models
from typing import List, Dict, Optional
from app.logging_config import get_logger

logger = get_logger(__name__)

class DynamicModelGenerator:
    @staticmethod
    def create_model_from_schema(fields: List[FieldConfig], schema_id: str) -> type[BaseModel]:
        """Create a Pydantic model from a list of field configurations"""
        field_definitions = {}
        
        for field in fields:
            field_type = DynamicModelGenerator.get_field_type(field.type)
            
            field_info = Field(
                description=field.description,
                default=None if not field.required else ...  # ... means required
            )
            
            # Add validation pattern if specified
            if field.validation_pattern:
                field_info = Field(
                    description=field.description,
                    default=None if not field.required else ...,
                    pattern=field.validation_pattern
                )
            
            field_definitions[field.name] = (field_type if field.required else Optional[field_type], field_info)
        
        # Add common fields that are always present in document extraction
        field_definitions.update({
            'source_documents': (List[SourceDocument], ...),
            'citations': (Dict[str, str], Field(default_factory=dict)),
            'bounding_boxes': (Dict[str, BoundingBox], Field(default_factory=dict))
        })
        
        # Create the dynamic model
        model_name = f"Dynamic_{schema_id.replace('-', '_').replace(' ', '_')}_Model"
        dynamic_model = create_model(
            model_name,
            **field_definitions
        )
        
        logger.info(f"Created dynamic model: {model_name} with {len(fields)} custom fields")
        return dynamic_model
    
    @staticmethod
    def get_field_type(field_type: FieldType):
        """Map field types to Python types"""
        type_mapping = {
            FieldType.string: str,
            FieldType.integer: int,
            FieldType.float: float,
            FieldType.boolean: bool,
            FieldType.date: str,  # Could use datetime if needed
            FieldType.email: str,
            FieldType.phone: str,
            FieldType.address: str,
        }
        return type_mapping.get(field_type, str)

    @staticmethod
    def model_to_schema(model: type[BaseModel]) -> dict:
        """Convert a Pydantic model back to a schema definition for reference"""
        schema_json = model.model_json_schema()
        properties = schema_json.get('properties', {})
        
        fields = []
        for field_name, field_info in properties.items():
            # Skip the common fields that are always present
            if field_name in ['source_documents', 'citations', 'bounding_boxes']:
                continue
                
            field_type = field_info.get('type', 'string')
            pydantic_type = DynamicModelGenerator.json_type_to_py_type(field_type)
            
            field_config = FieldConfig(
                name=field_name,
                type=pydantic_type,
                description=field_info.get('description', ''),
                required=field_name in schema_json.get('required', []),
                validation_pattern=field_info.get('pattern')
            )
            fields.append(field_config)
        
        return {
            'properties': properties,
            'required': schema_json.get('required', []),
            'title': schema_json.get('title', 'Unknown Model')
        }

    @staticmethod
    def json_type_to_py_type(json_type: str) -> FieldType:
        """Convert JSON schema type to FieldType"""
        mapping = {
            'string': FieldType.string,
            'integer': FieldType.integer,
            'number': FieldType.float,
            'boolean': FieldType.boolean,
        }
        return mapping.get(json_type, FieldType.string)