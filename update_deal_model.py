
"""
Migration script to update Deal model to use contact_id instead of client_id
Run this once to update existing database
"""

from sqlalchemy import text
from extensions.db import db
from app import create_app

def migrate_deal_table():
    app = create_app()
    with app.app_context():
        try:
            # Add the new contact_id column
            db.session.execute(text("""
                ALTER TABLE deal ADD COLUMN contact_id INTEGER;
            """))
            
            # Add foreign key constraint
            db.session.execute(text("""
                ALTER TABLE deal ADD CONSTRAINT fk_deal_contact 
                FOREIGN KEY (contact_id) REFERENCES contact(id);
            """))
            
            # Migrate existing client_id data to contact_id
            # This finds the contact_id for each existing client record
            db.session.execute(text("""
                UPDATE deal 
                SET contact_id = (
                    SELECT client.contact_id 
                    FROM client 
                    WHERE client.id = deal.client_id
                )
                WHERE deal.client_id IS NOT NULL;
            """))
            
            # Drop the old client_id column
            db.session.execute(text("""
                ALTER TABLE deal DROP COLUMN client_id;
            """))
            
            db.session.commit()
            print("Deal table migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")
            print("You may need to run this manually or adjust based on your database setup")

if __name__ == '__main__':
    migrate_deal_table()
