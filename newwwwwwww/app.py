# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grocery_store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50))
    description = db.Column(db.Text)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    category = db.relationship('Category', backref=db.backref('products', lazy=True))

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))
    product = db.relationship('Product', backref=db.backref('in_carts', lazy=True))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_amount = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('orders', lazy=True))

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    order = db.relationship('Order', backref=db.backref('items', lazy=True))
    product = db.relationship('Product', backref=db.backref('in_orders', lazy=True))

# Voice Assistant Class
class VoiceAssistant:
    def __init__(self):
        self.commands = {
            'login': ['login', 'sign in'],
            'register': ['register', 'sign up'],
            'products': ['products', 'items', 'show products'],
            'cart': ['cart', 'my cart', 'shopping cart'],
            'orders': ['orders', 'my orders'],
            'search': ['search', 'find'],
            'checkout': ['checkout', 'place order'],
            'help': ['help', 'what can i do'],
            'logout': ['logout', 'sign out']
        }
    
    def process_command(self, command):
        if not command:
            return None
            
        command = command.lower()
        
        # Check for specific commands
        for action, keywords in self.commands.items():
            for keyword in keywords:
                if keyword in command:
                    return action
        
        # Handle search queries
        if 'search for' in command:
            query = command.replace('search for', '').strip()
            return ('search', query)
        
        # Handle adding to cart
        if 'add to cart' in command or 'buy' in command:
            # Extract product name/number
            words = command.split()
            for i, word in enumerate(words):
                if word.isdigit() or word in ['first', 'second', 'third', 'fourth', 'fifth']:
                    return ('add_to_cart', word)
        
        return None

voice_assistant = VoiceAssistant()

# Routes
@app.route('/')
def index():
    categories = Category.query.all()
    featured_products = Product.query.limit(8).all()
    return render_template('index.html', 
                         categories=categories, 
                         featured_products=featured_products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/products')
def products():
    category_id = request.args.get('category_id')
    search = request.args.get('search')
    
    query = Product.query
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.all()
    categories = Category.query.all()
    
    return render_template('products.html', 
                         products=products, 
                         categories=categories,
                         selected_category=category_id,
                         search_query=search)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    product = Product.query.get_or_404(product_id)
    quantity = int(request.json.get('quantity', 1))
    
    # Check if item already in cart
    cart_item = Cart.query.filter_by(
        user_id=session['user_id'], 
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=session['user_id'], 
                        product_id=product_id, 
                        quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'{product.name} added to cart',
        'cart_count': get_cart_count()
    })

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash('Please login to view your cart', 'error')
        return redirect(url_for('login'))
    
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart/<int:cart_id>', methods=['POST'])
def update_cart(cart_id):
    cart_item = Cart.query.get_or_404(cart_id)
    
    if cart_item.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    action = request.json.get('action')
    
    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease' and cart_item.quantity > 1:
        cart_item.quantity -= 1
    elif action == 'remove':
        db.session.delete(cart_item)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'cart_count': get_cart_count(),
        'subtotal': cart_item.product.price * cart_item.quantity if action != 'remove' else 0
    })

@app.route('/get_cart_count')
def get_cart_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    
    count = Cart.query.filter_by(user_id=session['user_id']).count()
    return jsonify({'count': count})

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        flash('Please login to checkout', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        user = User.query.get(session['user_id'])
        cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
        
        if not cart_items:
            flash('Your cart is empty', 'error')
            return redirect(url_for('view_cart'))
        
        total_amount = sum(item.product.price * item.quantity for item in cart_items)
        delivery_address = request.form['address']
        phone = request.form['phone']
        payment_method = request.form['payment_method']
        
        # Create order
        order = Order(
            user_id=session['user_id'],
            total_amount=total_amount,
            delivery_address=delivery_address,
            phone=phone,
            payment_method=payment_method
        )
        db.session.add(order)
        db.session.flush()  # Get the order ID
        
        # Create order items
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            db.session.add(order_item)
        
        # Clear cart
        Cart.query.filter_by(user_id=session['user_id']).delete()
        
        db.session.commit()
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_id=order.id))
    
    user = User.query.get(session['user_id'])
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    return render_template('checkout.html', 
                         user=user, 
                         cart_items=cart_items, 
                         total=total)

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != session['user_id']:
        flash('Unauthorized access', 'error')
        return redirect(url_for('index'))
    
    return render_template('order_confirmation.html', order=order)

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        flash('Please login to view your orders', 'error')
        return redirect(url_for('login'))
    
    user_orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders)

@app.route('/voice_command', methods=['POST'])
def voice_command():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login first'})
    
    command = request.json.get('command')
    result = voice_assistant.process_command(command)
    
    if result:
        if result == 'cart':
            return jsonify({'success': True, 'redirect': url_for('view_cart')})
        elif result == 'products':
            return jsonify({'success': True, 'redirect': url_for('products')})
        elif result == 'orders':
            return jsonify({'success': True, 'redirect': url_for('orders')})
        elif result == 'checkout':
            return jsonify({'success': True, 'redirect': url_for('checkout')})
        elif isinstance(result, tuple) and result[0] == 'search':
            return jsonify({'success': True, 'redirect': url_for('products', search=result[1])})
    
    return jsonify({'success': False, 'message': 'Command not recognized'})

# Admin Routes
@app.route('/admin')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    total_products = Product.query.count()
    total_orders = Order.query.count()
    total_users = User.query.count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_products=total_products,
                         total_orders=total_orders,
                         total_users=total_users,
                         recent_orders=recent_orders)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Simple admin authentication (in production, use proper auth)
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/products')
def admin_products():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('admin/products.html', products=products, categories=categories)

@app.route('/admin/add_product', methods=['POST'])
def add_product():
    if 'admin' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    name = request.form['name']
    description = request.form['description']
    price = float(request.form['price'])
    category_id = int(request.form['category_id'])
    stock = int(request.form.get('stock', 0))
    
    # Handle image upload
    image = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = f'uploads/{filename}'
    
    product = Product(
        name=name,
        description=description,
        price=price,
        category_id=category_id,
        stock=stock,
        image=image
    )
    
    db.session.add(product)
    db.session.commit()
    
    flash('Product added successfully', 'success')
    return redirect(url_for('admin_products'))

# Helper function
def get_cart_count():
    if 'user_id' not in session:
        return 0
    return Cart.query.filter_by(user_id=session['user_id']).count()

# Initialize database and sample data
def init_db():
    with app.app_context():
        db.create_all()
        
        # Add sample categories if none exist
        if Category.query.count() == 0:
            categories = [
                Category(name='Fruits & Vegetables', icon='fas fa-apple-alt', 
                        description='Fresh fruits and vegetables'),
                Category(name='Beverages', icon='fas fa-wine-bottle', 
                        description='Drinks and beverages'),
                Category(name='Bakery', icon='fas fa-bread-slice', 
                        description='Fresh baked goods'),
                Category(name='Dairy & Eggs', icon='fas fa-egg', 
                        description='Dairy products and eggs'),
                Category(name='Meat & Seafood', icon='fas fa-fish', 
                        description='Fresh meat and seafood'),
                Category(name='Frozen Foods', icon='fas fa-ice-cream', 
                        description='Frozen food items')
            ]
            db.session.bulk_save_objects(categories)
            db.session.commit()
        
        # Add sample products if none exist
        if Product.query.count() == 0:
            products = [
                Product(name='Organic Apples', description='Fresh, crisp organic apples from local farms', 
                       price=4.99, category_id=1, stock=50, image='uploads/apples.jpg'),
                Product(name='Whole Wheat Bread', description='Freshly baked whole wheat bread, no preservatives', 
                       price=3.49, category_id=3, stock=30, image='uploads/bread.jpg'),
                Product(name='Organic Milk', description='Fresh organic milk from grass-fed cows', 
                       price=5.99, category_id=4, stock=20, image='uploads/milk.jpg'),
                Product(name='Free Range Eggs', description='Farm fresh free range eggs, pack of 12', 
                       price=4.29, category_id=4, stock=40, image='uploads/eggs.jpg'),
                Product(name='Orange Juice', description='100% pure orange juice, no added sugar', 
                       price=3.99, category_id=2, stock=25, image='uploads/juice.jpg'),
                Product(name='Salmon Fillet', description='Fresh Atlantic salmon fillet', 
                       price=12.99, category_id=5, stock=15, image='uploads/salmon.jpg')
            ]
            db.session.bulk_save_objects(products)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)