"""Authentication blueprint for login/logout/register"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import StringField, PasswordField, validators
from flask_wtf import FlaskForm

from extensions.db import db
from models.user import User
from models.role import Role
from models.access_request import AccessRequest
from utils.decorators import admin_required

auth_bp = Blueprint('auth', __name__)


class LoginForm(FlaskForm):
    """Login form"""
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    password = PasswordField('Password', [validators.DataRequired()])


class RegisterForm(FlaskForm):
    """Register form (admin only)"""
    first_name = StringField('First Name', [validators.DataRequired(), validators.Length(max=50)])
    last_name = StringField('Last Name', [validators.DataRequired(), validators.Length(max=50)])
    email = StringField('Email', [validators.DataRequired(), validators.Email(), validators.Length(max=120)])
    password = PasswordField('Password', [validators.DataRequired(), validators.Length(min=8)])


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.is_active and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout route"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    """User registration"""
    from utils.forms import UserForm
    from models.role import Role

    form = UserForm()
    roles = Role.query.all()

    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html', form=form, roles=roles)

        # Create new user
        user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            is_active=form.is_active.data
        )

        # Assign roles
        selected_role_names = request.form.getlist('roles')
        for role_name in selected_role_names:
            role = Role.query.filter_by(name=role_name).first()
            if role:
                user.roles.append(role)

        db.session.add(user)
        db.session.commit()

        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form, roles=roles)


@auth_bp.route('/request-access', methods=['POST'])
def request_access():
    """Handle access request submissions"""
    try:
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        company = request.form.get('company', '').strip()
        reason = request.form.get('reason', '').strip()

        # Basic validation
        if not all([first_name, last_name, email, reason]):
            return jsonify({'success': False, 'message': 'All required fields must be filled.'}), 400

        # Check if email already exists as a user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'success': False, 'message': 'An account with this email already exists.'}), 400

        # Check if there's already a pending request for this email
        existing_request = AccessRequest.query.filter_by(email=email, status='pending').first()
        if existing_request:
            return jsonify({'success': False, 'message': 'There is already a pending access request for this email.'}), 400

        # Create new access request
        access_request = AccessRequest(
            first_name=first_name,
            last_name=last_name,
            email=email,
            company=company if company else None,
            reason=reason
        )

        db.session.add(access_request)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Access request submitted successfully.'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred while submitting your request.'}), 500