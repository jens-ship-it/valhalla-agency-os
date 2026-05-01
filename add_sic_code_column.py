
#!/usr/bin/env python3
"""
Migration script to add sic_code column to entity table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions.db import db
from sqlalchemy import text

def main():
    app = create_app()
    
    with app.app_context():
        # Add the sic_code column to the entity table
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='entity' AND column_name='sic_code'
            """))
            
            if result.fetchone():
                print("✓ sic_code column already exists in entity table")
                return True
            
            # Add the column
            db.session.execute(text('ALTER TABLE entity ADD COLUMN sic_code VARCHAR(10)'))
            db.session.commit()
            print("✓ Added sic_code column to entity table")
        except Exception as e:
            print(f"✗ Error adding sic_code column: {e}")
            db.session.rollback()
            return False
        
        print("✓ Migration completed successfully")
        return True

if __name__ == '__main__':
    if main():
        print("\nMigration completed. You can now use the SIC Code field in organization forms.")
    else:
        print("\nMigration failed. Please check the error messages above.")
        sys.exit(1)
