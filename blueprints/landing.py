"""Landing page blueprint for public-facing marketing site"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from extensions.db import db
from models.demo_request import DemoRequest
from forms.landing import DemoRequestForm

landing_bp = Blueprint('landing', __name__)


@landing_bp.route('/')
def index():
    """Public landing page - redirect logged-in users to dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = DemoRequestForm()
    return render_template('landing/public.html', form=form)


@landing_bp.route('/demo-request', methods=['POST'])
def demo_request():
    """Handle demo request submissions"""
    form = DemoRequestForm()
    
    if form.validate_on_submit():
        try:
            demo = DemoRequest(
                name=form.name.data.strip(),
                email=form.email.data.strip().lower(),
                company=form.company.data.strip() if form.company.data else None,
                team_size=form.team_size.data if form.team_size.data else None,
                notes=form.notes.data.strip() if form.notes.data else None,
                status='pending'
            )
            
            db.session.add(demo)
            db.session.commit()
            
            flash('Thank you for your interest! We\'ll be in touch soon to schedule your demo.', 'success')
            return redirect(url_for('landing.index'))
        except Exception as e:
            db.session.rollback()
            flash('Error submitting request. Please try again.', 'danger')
            return redirect(url_for('landing.index'))
    else:
        # Form validation failed
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'danger')
        return redirect(url_for('landing.index'))


@landing_bp.route('/privacy.pdf')
def privacy_pdf():
    """Privacy policy placeholder"""
    return "Privacy Policy PDF - Coming Soon", 200, {'Content-Type': 'text/plain'}
