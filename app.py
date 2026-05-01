"""
Valhalla Agency OS - Flask Application Factory
Production-ready insurance agency management system
"""
import os
import logging
from flask import Flask, render_template, redirect, url_for
from flask_login import login_required
from markupsafe import Markup

from config import Config
from extensions.db import db
from extensions.migrate import migrate
from extensions.login import login_manager
from extensions.bcrypt import bcrypt
from extensions.csrf import csrf

# Import all models to ensure they're registered with SQLAlchemy
from models import (
    User, Role, Contact, Client, ContactLink, Entity, VendorDetail,
    GroupPolicy, IndividualPolicy, ServiceTicket, ServiceNote, Deal
)

# Import blueprints
from blueprints.auth import auth_bp
from blueprints.admin import admin_bp
from blueprints.service import service_bp
from blueprints.accounts import accounts_bp
from blueprints.vendors import vendors_bp
from blueprints.sales import sales_bp
from blueprints.contacts import contacts_bp
from blueprints.policies import policies_bp
from blueprints.landing import landing_bp


def create_app(config_class=Config):
    """Application factory function"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging
    logging.basicConfig(level=logging.DEBUG)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)

    # Register template filters
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to HTML line breaks"""
        if text is None:
            return ''
        return Markup(str(text).replace('\n', '<br>\n'))

    # Register blueprints
    app.register_blueprint(landing_bp)  # Public landing page at root
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(service_bp, url_prefix='/service')
    app.register_blueprint(accounts_bp, url_prefix='/accounts')
    app.register_blueprint(vendors_bp, url_prefix='/vendors')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(contacts_bp, url_prefix='/contacts')
    app.register_blueprint(policies_bp, url_prefix='/policies')

    # Dashboard route (authenticated)
    @app.route('/dashboard')
    @login_required
    def index():
        return render_template('index.html')

    # CLI commands
    @app.cli.command()
    def seed():
        """Seed the database with initial data"""
        from seeds.seed import seed_database
        seed_database()
        print("Database seeded successfully!")

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)