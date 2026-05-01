
"""Migration script to add missing columns to deal table"""
from app import create_app
from extensions.db import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Add missing columns to deal table
        print("Adding missing columns to deal table...")
        
        # Check if est_close_date exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='deal' AND column_name='est_close_date'
        """))
        
        if not result.fetchone():
            print("Adding est_close_date column...")
            db.session.execute(text("ALTER TABLE deal ADD COLUMN est_close_date DATE"))
        
        # Check if est_premium_value exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='deal' AND column_name='est_premium_value'
        """))
        
        if not result.fetchone():
            print("Adding est_premium_value column...")
            db.session.execute(text("ALTER TABLE deal ADD COLUMN est_premium_value NUMERIC(12,2)"))
        
        # Check if recurring exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='deal' AND column_name='recurring'
        """))
        
        if not result.fetchone():
            print("Adding recurring column...")
            db.session.execute(text("ALTER TABLE deal ADD COLUMN recurring VARCHAR(20) NOT NULL DEFAULT 'Recurring'"))
        
        # Check if actual_close_date exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='deal' AND column_name='actual_close_date'
        """))
        
        if not result.fetchone():
            print("Adding actual_close_date column...")
            db.session.execute(text("ALTER TABLE deal ADD COLUMN actual_close_date DATE"))
        
        # Check if product_type exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='deal' AND column_name='product_type'
        """))
        
        if not result.fetchone():
            print("Adding product_type column...")
            db.session.execute(text("ALTER TABLE deal ADD COLUMN product_type VARCHAR(100)"))
        
        # Check if competition exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='deal' AND column_name='competition'
        """))
        
        if not result.fetchone():
            print("Adding competition column...")
            db.session.execute(text("ALTER TABLE deal ADD COLUMN competition VARCHAR(200)"))
        
        # Check if next_step exists
        result = db.session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='deal' AND column_name='next_step'
        """))
        
        if not result.fetchone():
            print("Adding next_step column...")
            db.session.execute(text("ALTER TABLE deal ADD COLUMN next_step TEXT"))
        
        db.session.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        db.session.rollback()
