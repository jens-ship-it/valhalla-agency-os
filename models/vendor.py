"""Vendor model as wrapper around Entity + VendorDetail"""
from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.orm import relationship, object_session
from extensions.db import db
from models.entity import Entity, VendorDetail


class Vendor:
    """
    Wrapper class that provides a unified interface for vendors using Entity + VendorDetail.
    This maintains compatibility with existing vendor blueprint code.
    """
    
    def __init__(self, entity=None, **kwargs):
        """Initialize vendor, either from existing entity or create new one"""
        if entity:
            # Wrapping existing entity
            self._entity = entity
            self._vendor_detail = entity.vendor_detail
        else:
            # Creating new vendor
            self._entity = None
            self._vendor_detail = None
            
            # Store kwargs for later use when saving
            self._kwargs = kwargs
    
    @classmethod
    def _get_query(cls):
        """Get base query for vendors (entities with vendor details)"""
        return db.session.query(Entity).join(VendorDetail)
    
    @classmethod 
    def query(cls):
        """Provide query interface similar to SQLAlchemy models"""
        class VendorQuery:
            @staticmethod
            def get_or_404(vendor_id):
                entity = Entity.query.get_or_404(vendor_id)
                if not entity.is_vendor:
                    from werkzeug.exceptions import NotFound
                    raise NotFound(f"Vendor with id {vendor_id} not found")
                return Vendor(entity=entity)
            
            @staticmethod
            def filter(*args, **kwargs):
                return VendorQueryFilter()
            
            @staticmethod
            def filter_by(**kwargs):
                return VendorQueryFilter()
                
            @staticmethod
            def order_by(*args):
                return VendorQueryFilter()
                
        return VendorQuery()
    
    @property
    def id(self):
        return self._entity.id if self._entity else None
    
    @property
    def name(self):
        return self._entity.name if self._entity else self._kwargs.get('name')
    
    @name.setter
    def name(self, value):
        if self._entity:
            self._entity.name = value
        else:
            self._kwargs['name'] = value
    
    @property
    def vendor_type(self):
        return self._vendor_detail.vendor_type if self._vendor_detail else self._kwargs.get('vendor_type')
    
    @vendor_type.setter
    def vendor_type(self, value):
        if self._vendor_detail:
            self._vendor_detail.vendor_type = value
        else:
            self._kwargs['vendor_type'] = value
    
    @property
    def role_description(self):
        return self._vendor_detail.description if self._vendor_detail else self._kwargs.get('role_description')
    
    @role_description.setter
    def role_description(self, value):
        if self._vendor_detail:
            self._vendor_detail.description = value
        else:
            self._kwargs['role_description'] = value
    
    @property
    def phone(self):
        return self._entity.phone if self._entity else self._kwargs.get('phone')
    
    @phone.setter
    def phone(self, value):
        if self._entity:
            self._entity.phone = value
        else:
            self._kwargs['phone'] = value
    
    @property
    def email(self):
        return self._entity.email if self._entity else self._kwargs.get('email')
    
    @email.setter
    def email(self, value):
        if self._entity:
            self._entity.email = value
        else:
            self._kwargs['email'] = value
    
    @property
    def website(self):
        return self._entity.website if self._entity else self._kwargs.get('website')
    
    @website.setter
    def website(self, value):
        if self._entity:
            self._entity.website = value
        else:
            self._kwargs['website'] = value
    
    @property
    def address_line1(self):
        return self._entity.address_line1 if self._entity else self._kwargs.get('address_line1')
    
    @address_line1.setter
    def address_line1(self, value):
        if self._entity:
            self._entity.address_line1 = value
        else:
            self._kwargs['address_line1'] = value
    
    @property
    def address_line2(self):
        return self._entity.address_line2 if self._entity else self._kwargs.get('address_line2')
    
    @address_line2.setter
    def address_line2(self, value):
        if self._entity:
            self._entity.address_line2 = value
        else:
            self._kwargs['address_line2'] = value
    
    @property
    def city(self):
        return self._entity.city if self._entity else self._kwargs.get('city')
    
    @city.setter
    def city(self, value):
        if self._entity:
            self._entity.city = value
        else:
            self._kwargs['city'] = value
    
    @property
    def state(self):
        return self._entity.state if self._entity else self._kwargs.get('state')
    
    @state.setter
    def state(self, value):
        if self._entity:
            self._entity.state = value
        else:
            self._kwargs['state'] = value
    
    @property
    def zip(self):
        return self._entity.zip if self._entity else self._kwargs.get('zip')
    
    @zip.setter
    def zip(self, value):
        if self._entity:
            self._entity.zip = value
        else:
            self._kwargs['zip'] = value
    
    @property
    def notes(self):
        return self._entity.notes if self._entity else self._kwargs.get('notes')
    
    @notes.setter
    def notes(self, value):
        if self._entity:
            self._entity.notes = value
        else:
            self._kwargs['notes'] = value
    
    @property
    def status(self):
        return self._entity.status if self._entity else self._kwargs.get('status', 'active')
    
    @status.setter
    def status(self, value):
        if self._entity:
            self._entity.status = value
        else:
            self._kwargs['status'] = value
    
    @property
    def created_at(self):
        return self._entity.created_at if self._entity else None
    
    def save(self):
        """Save the vendor to database"""
        if not self._entity:
            # Create new entity
            self._entity = Entity(
                name=self._kwargs.get('name'),
                phone=self._kwargs.get('phone'),
                email=self._kwargs.get('email'),
                website=self._kwargs.get('website'),
                address_line1=self._kwargs.get('address_line1'),
                address_line2=self._kwargs.get('address_line2'),
                city=self._kwargs.get('city'),
                state=self._kwargs.get('state'),
                zip=self._kwargs.get('zip'),
                notes=self._kwargs.get('notes'),
                status=self._kwargs.get('status', 'active')
            )
            db.session.add(self._entity)
            db.session.flush()  # Get the ID
            
            # Create vendor detail
            self._vendor_detail = VendorDetail(
                entity_id=self._entity.id,
                vendor_type=self._kwargs.get('vendor_type'),
                description=self._kwargs.get('role_description')
            )
            db.session.add(self._vendor_detail)
        
        db.session.commit()
        return self
    
    @classmethod
    def get_vendor_type_choices(cls):
        """Return list of vendor type choices for forms"""
        return VendorDetail.get_vendor_type_choices()
    
    def __repr__(self):
        return f'<Vendor {self.name} ({self.vendor_type})>'


class VendorQueryFilter:
    """Helper class to provide query filtering interface"""
    
    def __init__(self):
        self._query = Entity.query.join(VendorDetail)
    
    def filter(self, *criterion):
        self._query = self._query.filter(*criterion)
        return self
    
    def filter_by(self, **kwargs):
        # Handle simple field=value filters
        entity_filters = {}
        vendor_filters = {}
        
        for key, value in kwargs.items():
            if key in ['name', 'phone', 'email', 'website', 'address_line1', 'address_line2', 
                      'city', 'state', 'zip', 'notes', 'status']:
                entity_filters[key] = value
            elif key == 'vendor_type':
                vendor_filters[key] = value
        
        if entity_filters:
            self._query = self._query.filter_by(**entity_filters)
        if vendor_filters:
            self._query = self._query.filter(VendorDetail.vendor_type == vendor_filters['vendor_type'])
        
        return self
    
    def order_by(self, *criterion):
        self._query = self._query.order_by(*criterion)
        return self
    
    def paginate(self, page=1, per_page=20, error_out=True):
        """Return paginated results as Vendor objects"""
        paginated = self._query.paginate(page=page, per_page=per_page, error_out=error_out)
        
        # Convert Entity objects to Vendor objects
        vendor_items = [Vendor(entity=entity) for entity in paginated.items]
        
        # Create a simple paginated result object
        class PaginatedVendors:
            def __init__(self, items, page, per_page, total, pages, has_prev, has_next, prev_num, next_num):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = pages
                self.has_prev = has_prev
                self.has_next = has_next
                self.prev_num = prev_num
                self.next_num = next_num
                
            def iter_pages(self):
                """Iterator for page numbers"""
                for page_num in range(1, self.pages + 1):
                    yield page_num
                
        return PaginatedVendors(
            vendor_items, 
            paginated.page, 
            paginated.per_page, 
            paginated.total,
            paginated.pages,
            paginated.has_prev,
            paginated.has_next,
            paginated.prev_num,
            paginated.next_num
        )


# Add class attribute for query interface
Vendor.query = Vendor.query()