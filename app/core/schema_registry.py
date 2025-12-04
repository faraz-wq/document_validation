import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from app.logging_config import get_logger
from app.schemas.schema_models import SchemaDefinition, FieldConfig


logger = get_logger(__name__)

class SchemaRegistry:
    def __init__(self, db_path: str = "./schemas_v1.db"):
        # Ensure data directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Schemas table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_schemas (
                schema_id TEXT PRIMARY KEY,
                schema_name TEXT NOT NULL,
                description TEXT,
                fields_json TEXT NOT NULL,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Schema permissions table (for multi-tenant access control)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schema_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                permission_level TEXT NOT NULL, -- 'read', 'write', 'admin'
                FOREIGN KEY (schema_id) REFERENCES user_schemas(schema_id)
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Schema database initialized at {self.db_path}")

    def register_schema(self, schema_def: SchemaDefinition) -> bool:
        """Register a new user-defined schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO user_schemas 
                (schema_id, schema_name, description, fields_json, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (
                schema_def.schema_id,
                schema_def.schema_name,
                schema_def.description,
                json.dumps([field.dict() for field in schema_def.fields]),
                schema_def.created_by
            ))
            
            # Grant permission to the creator
            cursor.execute("""
                INSERT INTO schema_permissions 
                (schema_id, user_id, permission_level)
                VALUES (?, ?, 'admin')
            """, (schema_def.schema_id, schema_def.created_by))
            
            conn.commit()
            logger.info(f"Registered schema: {schema_def.schema_id}")
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"Schema ID already exists: {e}")
            return False
        except Exception as e:
            logger.error(f"Error registering schema: {e}", exc_info=True)
            return False
        finally:
            conn.close()
    
    def get_schema(self, schema_id: str, user_id: str) -> Optional[SchemaDefinition]:
        """Retrieve a user schema with permission check"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First check if user has permission
        cursor.execute("""
            SELECT permission_level FROM schema_permissions
            WHERE schema_id = ? AND user_id = ?
        """, (schema_id, user_id))
        
        perm = cursor.fetchone()
        if not perm:
            conn.close()
            logger.warning(f"User {user_id} has no permission for schema {schema_id}")
            return None  # No permission
        
        # Get the schema definition
        cursor.execute("""
            SELECT schema_name, description, fields_json, created_by, created_at
            FROM user_schemas WHERE schema_id = ?
        """, (schema_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return None
        
        schema_name, description, fields_json, created_by, created_at = result
        
        fields = [FieldConfig(**field) for field in json.loads(fields_json)]
        
        conn.close()
        return SchemaDefinition(
            schema_id=schema_id,
            schema_name=schema_name,
            description=description,
            fields=fields,
            created_by=created_by,
            created_at=created_at
        )
    
    def list_user_schemas(self, user_id: str) -> List[SchemaDefinition]:
        """List all schemas accessible to a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.schema_id, s.schema_name, s.description, s.fields_json, s.created_by, s.created_at
            FROM user_schemas s
            JOIN schema_permissions sp ON s.schema_id = sp.schema_id
            WHERE sp.user_id = ?
        """, (user_id,))
        
        schemas = []
        for row in cursor.fetchall():
            schema_id, schema_name, description, fields_json, created_by, created_at = row
            fields = [FieldConfig(**field) for field in json.loads(fields_json)]
            
            schemas.append(SchemaDefinition(
                schema_id=schema_id,
                schema_name=schema_name,
                description=description,
                fields=fields,
                created_by=created_by,
                created_at=created_at
            ))
        
        conn.close()
        return schemas

    def update_schema(self, schema_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing schema if user has permission"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if user has admin permission
            cursor.execute("""
                SELECT permission_level FROM schema_permissions
                WHERE schema_id = ? AND user_id = ? AND permission_level = 'admin'
            """, (schema_id, user_id))
            
            if not cursor.fetchone():
                logger.warning(f"User {user_id} does not have admin permission to update schema {schema_id}")
                return False
            
            # Update the schema
            if 'fields' in updates:
                fields_json = json.dumps([field if isinstance(field, dict) else field.dict() 
                                         for field in updates['fields']])
                cursor.execute("""
                    UPDATE user_schemas 
                    SET schema_name = ?, description = ?, fields_json = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE schema_id = ?
                """, (
                    updates.get('schema_name', ''),
                    updates.get('description', ''),
                    fields_json,
                    schema_id
                ))
            else:
                cursor.execute("""
                    UPDATE user_schemas 
                    SET schema_name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE schema_id = ?
                """, (
                    updates.get('schema_name', ''),
                    updates.get('description', ''),
                    schema_id
                ))
            
            conn.commit()
            logger.info(f"Updated schema: {schema_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error updating schema: {e}", exc_info=True)
            return False
        finally:
            conn.close()
    
    def delete_schema(self, schema_id: str, user_id: str) -> bool:
        """Delete a schema if user has admin permission"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if user has admin permission
            cursor.execute("""
                SELECT permission_level FROM schema_permissions
                WHERE schema_id = ? AND user_id = ? AND permission_level = 'admin'
            """, (schema_id, user_id))
            
            if not cursor.fetchone():
                logger.warning(f"User {user_id} does not have admin permission to delete schema {schema_id}")
                return False
            
            # Delete schema and permissions
            cursor.execute("DELETE FROM schema_permissions WHERE schema_id = ?", (schema_id,))
            cursor.execute("DELETE FROM user_schemas WHERE schema_id = ?", (schema_id,))
            
            conn.commit()
            logger.info(f"Deleted schema: {schema_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting schema: {e}", exc_info=True)
            return False
        finally:
            conn.close()


# Global schema registry instance
schema_registry = SchemaRegistry()