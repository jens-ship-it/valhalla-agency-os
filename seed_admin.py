
"""Script to create initial admin user"""
from werkzeug.security import generate_password_hash
from extensions.db import db
from models.user import User
from models.role import Role
from app import create_app

def create_initial_admin():
    app = create_app()
    
    with app.app_context():
        # Create admin role if it doesn't exist
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator role')
            db.session.add(admin_role)
        
        # Check if admin user already exists
        admin_user = User.query.filter_by(email='jens@valhallaba.com').first()
        if not admin_user:
            admin_user = User(
                first_name='Jens',
                last_name='Admin',
                email='jens@valhallaba.com',
                password_hash=generate_password_hash('Dk4life1978!'),
                is_active=True
            )
            admin_user.roles.append(admin_role)
            db.session.add(admin_user)
            db.session.commit()
            print("Initial admin user created:")
            print("Email: jens@valhallaba.com")
            print("Password: Dk4life1978!")
            print("Please change this password immediately after first login!")
        else:
            print("Admin user already exists")

if __name__ == '__main__':
    create_initial_admin()
