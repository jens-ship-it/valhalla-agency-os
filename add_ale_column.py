
"""Migration script to add is_applicable_large_employer column to entity table"""
from app import create_app
from extensions.db import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Check if is_applicable_large_employer column exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='entity' AND column_name='is_applicable_large_employer'
        """))
        
        if not result.fetchone():
            print("Adding is_applicable_large_employer column to entity table...")
            db.session.execute(text("""
                ALTER TABLE entity 
                ADD COLUMN is_applicable_large_employer BOOLEAN NOT NULL DEFAULT FALSE
            """))
            db.session.commit()
            print("Column added successfully!")
        else:
            print("Column already exists.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        db.session.rollback()
