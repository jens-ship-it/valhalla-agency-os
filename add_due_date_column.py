
"""Migration script to add due_date column to service_ticket table"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions.db import db
from sqlalchemy import text

def add_due_date_column():
    """Add due_date column to service_ticket table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='service_ticket' AND column_name='due_date'
            """))
            
            if result.fetchone():
                print("due_date column already exists")
                return
            
            # Add the due_date column
            db.session.execute(text("""
                ALTER TABLE service_ticket 
                ADD COLUMN due_date DATE
            """))
            
            db.session.commit()
            print("Successfully added due_date column to service_ticket table")
            
        except Exception as e:
            print(f"Error adding due_date column: {e}")
            db.session.rollback()

if __name__ == "__main__":
    add_due_date_column()
