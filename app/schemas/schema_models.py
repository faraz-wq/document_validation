from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from enum import Enum


class FieldType(str, Enum):
    string = "string"
    integer = "integer"
    float = "float"
    boolean = "boolean"
    date = "date"
    email = "email"
    phone = "phone"
    address = "address"
    nested = "nested"


class FieldConfig(BaseModel):
    name: str
    type: FieldType
    description: str
    required: bool = True
    validation_pattern: Optional[str] = None
    nested_schema_id: Optional[str] = None  # For nested objects


class SchemaDefinition(BaseModel):
    schema_id: str
    schema_name: str
    description: str
    fields: List[FieldConfig]
    created_by: str
    created_at: str = ""


class SchemaTemplates:
    """Pre-defined templates that users can customize"""
    
    INVOICE_SCHEMA = {
        "schema_id": "invoice_template",
        "schema_name": "Invoice",
        "description": "Standard invoice schema",
        "fields": [
            {"name": "invoice_number", "type": "string", "required": True, "description": "Invoice number"},
            {"name": "invoice_date", "type": "date", "required": True, "description": "Invoice date"},
            {"name": "vendor_name", "type": "string", "required": True, "description": "Vendor name"},
            {"name": "total_amount", "type": "float", "required": True, "description": "Total amount"},
        ]
    }
    
    EMPLOYEE_SCHEMA = {
        "schema_id": "employee_template",
        "schema_name": "Employee Info",
        "description": "Employee information schema",
        "fields": [
            {"name": "employee_id", "type": "string", "required": True, "description": "Employee ID"},
            {"name": "name", "type": "string", "required": True, "description": "Employee name"},
            {"name": "email", "type": "email", "required": True, "description": "Employee email"},
            {"name": "department", "type": "string", "required": True, "description": "Department"},
            {"name": "hire_date", "type": "date", "required": True, "description": "Hire date"}
        ]
    }
    
    @staticmethod
    def get_templates() -> Dict[str, dict]:
        """Return all available templates"""
        return {
            "invoice": SchemaTemplates.INVOICE_SCHEMA,
            "employee": SchemaTemplates.EMPLOYEE_SCHEMA
        }