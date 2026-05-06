from config.settings import db

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Integer, nullable=False)
    area = db.Column(db.Float, nullable=False)  # in m²
    property_type = db.Column(db.String(50), nullable=False)  # e.g., apartment, house
    status = db.Column(db.String(50), nullable=False)  # e.g., for sale, sold
    is_featured = db.Column(db.Boolean, default=False)
    images = db.Column(db.Text)  # JSON string of image filenames
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())