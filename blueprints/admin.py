"""Admin blueprint for user and role management"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import or_

from extensions.db import db
from models.user import User
from models.role import Role
from models.access_request import AccessRequest
from utils.decorators import admin_required
from utils.forms import UserForm, SearchForm

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users')
@admin_required
def users():
    """List all users with search and pagination"""
    search_form = SearchForm()
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    query = User.query
    
    # Apply search filter
    if request.args.get('q'):
        search_term = f"%{request.args.get('q')}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.email.ilike(search_term)
            )
        )
    
    users = query.order_by(User.last_name, User.first_name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/users.html', users=users, search_form=search_form)


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create new user"""
    form = UserForm()
    roles = Role.query.all()
    
    if form.validate_on_submit():
        # Check if email already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered.', 'danger')
            return render_template('admin/user_form.html', form=form, roles=roles, user=None)
        
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
        
        flash(f'User {user.full_name} created successfully.', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_form.html', form=form, roles=roles, user=None)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit existing user"""
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    roles = Role.query.all()
    
    if form.validate_on_submit():
        # Check if email already exists (excluding current user)
        existing_user = User.query.filter(User.email == form.email.data, User.id != user_id).first()
        if existing_user:
            flash('Email already registered to another user.', 'danger')
            return render_template('admin/user_form.html', form=form, roles=roles, user=user)
        
        # Update user
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.is_active = form.is_active.data
        
        # Update password if provided
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
        
        # Update roles
        user.roles.clear()
        selected_role_names = request.form.getlist('roles')
        for role_name in selected_role_names:
            role = Role.query.filter_by(name=role_name).first()
            if role:
                user.roles.append(role)
        
        db.session.commit()
        
        flash(f'User {user.full_name} updated successfully.', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_form.html', form=form, roles=roles, user=user)


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.full_name} {status} successfully.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/roles')
@admin_required
def roles():
    """List all roles"""
    roles = Role.query.order_by(Role.name).all()
    return render_template('admin/roles.html', roles=roles)


@admin_bp.route('/access-requests')
@admin_required
def access_requests():
    """List all access requests"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'pending')
    per_page = 25
    
    query = AccessRequest.query
    
    if status_filter != 'all':
        query = query.filter(AccessRequest.status == status_filter)
    
    requests = query.order_by(AccessRequest.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/access_requests.html', requests=requests, status_filter=status_filter)


@admin_bp.route('/access-requests/<int:request_id>/approve', methods=['POST'])
@admin_required
def approve_access_request(request_id):
    """Approve an access request and create user account"""
    access_request = AccessRequest.query.get_or_404(request_id)
    
    if access_request.status != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('admin.access_requests'))
    
    try:
        # Create new user account
        user = User(
            first_name=access_request.first_name,
            last_name=access_request.last_name,
            email=access_request.email,
            password_hash=generate_password_hash('TempPassword123!'),  # They'll need to reset
            is_active=True
        )
        
        # Assign default role (you might want to make this configurable)
        default_role = Role.query.filter_by(name='service').first()
        if default_role:
            user.roles.append(default_role)
        
        db.session.add(user)
        
        # Update access request
        access_request.status = 'approved'
        access_request.reviewed_at = datetime.utcnow()
        access_request.reviewed_by_user_id = current_user.id
        
        db.session.commit()
        
        flash(f'Access request approved. User account created for {user.full_name}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error creating user account. Please try again.', 'danger')
    
    return redirect(url_for('admin.access_requests'))


@admin_bp.route('/access-requests/<int:request_id>/reject', methods=['POST'])
@admin_required
def reject_access_request(request_id):
    """Reject an access request"""
    access_request = AccessRequest.query.get_or_404(request_id)
    
    if access_request.status != 'pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('admin.access_requests'))
    
    admin_notes = request.form.get('admin_notes', '').strip()
    
    access_request.status = 'rejected'
    access_request.reviewed_at = datetime.utcnow()
    access_request.reviewed_by_user_id = current_user.id
    access_request.admin_notes = admin_notes if admin_notes else None
    
    db.session.commit()
    
    flash(f'Access request from {access_request.full_name} has been rejected.', 'success')
    return redirect(url_for('admin.access_requests'))
