from flask import Blueprint, render_template, request, redirect, url_for
from models import Property
from config.settings import db

main = Blueprint('main', __name__)

@main.route('/')
def index():
    featured_properties = Property.query.filter_by(is_featured=True).limit(6).all()
    return render_template('index.html', featured_properties=featured_properties)

@main.route('/properties')
def properties():
    query = Property.query
    # Simple filters
    location = request.args.get('location')
    property_type = request.args.get('type')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    bedrooms = request.args.get('bedrooms')

    if location:
        query = query.filter(Property.location.contains(location))
    if property_type:
        query = query.filter_by(property_type=property_type)
    if min_price:
        query = query.filter(Property.price >= float(min_price))
    if max_price:
        query = query.filter(Property.price <= float(max_price))
    if bedrooms:
        query = query.filter_by(bedrooms=int(bedrooms))

    properties_list = query.all()
    return render_template('properties.html', properties=properties_list)

@main.route('/property/<int:id>')
def property_detail(id):
    property = Property.query.get_or_404(id)
    similar_properties = Property.query.filter_by(property_type=property.property_type).filter(Property.id != id).limit(3).all()
    return render_template('property_detail.html', property=property, similar_properties=similar_properties)


@main.route('/sobre')
def about():
    return render_template('sobre.html')