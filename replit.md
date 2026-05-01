# Valhalla Agency OS

## Overview

Valhalla Agency OS is a comprehensive Flask-based insurance agency management system designed to handle client relationships, service operations, and business processes. The application provides a complete CRM solution with role-based access control (RBAC), service ticket management, contact tracking, and sales pipeline functionality. Built with modern web technologies, it offers a modular architecture that separates concerns while maintaining operational efficiency for insurance agencies.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Flask Application Structure
The application follows a blueprint-based modular architecture using Flask's application factory pattern. Core functionality is organized into distinct blueprints:

- **Auth Blueprint**: Handles user authentication with session management and bcrypt password hashing
- **Admin Blueprint**: Provides user and role management capabilities
- **Service Blueprint**: Manages service tickets and reporting workflows
- **Accounts Blueprint**: Handles organization and individual client management
- **Vendors Blueprint**: Manages vendor and partner relationships
- **Contacts Blueprint**: Universal contact management system
- **Sales Blueprint**: Basic sales pipeline tracking

### Database Design
Uses SQLAlchemy ORM with a flexible polymorphic relationship system:

- **Core Entities**: Users, Roles, Organizations, Individuals, Vendors
- **Service Management**: ServiceTickets with polymorphic client relationships
- **Universal Contacts**: Contact model with polymorphic linking to any entity type
- **Policy Tracking**: Group and Individual policies with carrier management
- **Sales Pipeline**: Deal tracking with client associations

The database supports both SQLite (development) and can be easily switched to PostgreSQL for production use.

### Authentication & Authorization
Implements Flask-Login for session management with a comprehensive RBAC system:

- **Role System**: Admin, Service, Account Management, Sales, Marketing roles
- **Access Control**: Decorator-based route protection with role validation
- **Session Security**: CSRF protection and secure session configuration

### Frontend Architecture
Server-side rendered templates with Bootstrap 5 for responsive design:

- **Template System**: Jinja2 with modular base templates and component reuse
- **Interactive Elements**: HTMX for dynamic interactions without full page reloads
- **Styling**: Bootstrap 5 with dark theme and Feather icons for consistency

### Form Management
WTForms integration with comprehensive validation:

- **Modular Forms**: Separate form classes for each entity type
- **Dynamic Field Population**: Context-aware dropdown population
- **CSRF Protection**: Built-in form security with Flask-WTF

### Service Status Workflow
Implements a five-stage service ticket lifecycle:
- not_started → started → started_waiting_on_someone_else → complete_pending_confirmation → complete

### Reporting System
Advanced service reporting with SQL-based aggregations:

- **Client Summaries**: Grouped statistics by organization/individual
- **User Performance**: Pivot-style breakdowns by assigned users
- **Export Capabilities**: CSV export functionality for data analysis

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web framework with blueprints and Jinja2 templating
- **SQLAlchemy**: ORM for database abstraction and relationship management
- **Flask-Login**: User session management and authentication
- **Flask-WTF**: Form handling with CSRF protection
- **Flask-Migrate**: Database migration management via Alembic

### Security & Validation
- **Flask-Bcrypt**: Password hashing and verification
- **WTForms**: Form validation and rendering
- **passlib**: Additional password security utilities

### Frontend Libraries
- **Bootstrap 5**: CSS framework with dark theme support
- **HTMX**: Dynamic HTML interactions
- **Feather Icons**: Consistent iconography system

### Database
- **SQLite**: Development database (easily replaceable with PostgreSQL)
- **Alembic**: Database schema versioning and migrations

### Development & Testing
- **pytest**: Unit testing framework
- **Flask-Migrate**: Database migration tools for schema evolution

The architecture is designed for production scalability while maintaining development simplicity, with clear separation of concerns and comprehensive error handling throughout the application stack.