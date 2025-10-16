from flask import Flask, render_template, redirect, url_for, request, session, flash
from models import db, User, Product, Cart, Order
from werkzeug.security import generate_password_hash, check_password_hash
import stripe

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
db.init_app(app)

from flask import jsonify

# --- Product API Endpoints ---
@app.route('/api/products', methods=['GET'])
def api_get_products():
    products = Product.query.all()
    return jsonify({
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "inventory": p.inventory,
                "category": p.category,
                "image_url": p.image_url
            } for p in products
        ]
    })

@app.route('/api/products/<int:product_id>', methods=['GET'])
def api_get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "inventory": product.inventory,
        "category": product.category,
        "image_url": product.image_url
    })

@app.route('/api/products', methods=['POST'])
def api_add_product():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.username != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    data = request.get_json()
    name = data.get('name')
    price = data.get('price')
    inventory = data.get('inventory')
    category = data.get('category')
    image_url = data.get('image_url', '')
    if not name or price is None or inventory is None:
        return jsonify({"error": "Missing required fields"}), 400
    try:
        price = float(price)
        inventory = int(inventory)
    except ValueError:
        return jsonify({"error": "Invalid price or inventory value"}), 400
    product = Product(name=name, price=price, inventory=inventory, category=category, image_url=image_url)
    db.session.add(product)
    db.session.commit()
    return jsonify({"message": "Product added", "id": product.id}), 201

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def api_update_product(product_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.username != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    product.name = data.get('name', product.name)
    product.price = float(data.get('price', product.price))
    product.inventory = int(data.get('inventory', product.inventory))
    product.category = data.get('category', product.category)
    product.image_url = data.get('image_url', product.image_url)
    db.session.commit()
    return jsonify({"message": "Product updated"})

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.username != 'admin':
        return jsonify({"error": "Admin access required"}), 403
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})

# Make current user available in all templates
@app.context_processor
def inject_user():
    user = None
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
    return dict(current_user=user)

# Stripe test keys (replace with your own for real use)
stripe.api_key = 'sk_test_51NxxxxxxxREPLACE_ME'
STRIPE_PUBLISHABLE_KEY = 'pk_test_51NxxxxxxxREPLACE_ME'

# Remove from cart route
@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cart_item = Cart.query.get_or_404(cart_id)
    if cart_item.user_id == session['user_id']:
        db.session.delete(cart_item)
        db.session.commit()
    return redirect(url_for('cart'))


@app.route('/admin/product/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    """
    Allows an admin user to edit the details of a product by its ID.
    Accessible only to users with the username 'admin'.
    Handles GET requests to display the edit form and POST requests to update product details.
    """
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.username != 'admin':
        return redirect(url_for('login'))
    product = Product.query.get_or_404(product_id)
    # Expected form fields: 'name' (str), 'price' (float), 'inventory' (int), 'image_url' (str, optional)
    if request.method == 'POST':
        product.name = request.form['name']
        try:
            product.price = float(request.form['price'])
        except ValueError:
            flash('Invalid price value. Please enter a valid number.')
        inventory_input = request.form.get('inventory', 0)
        try:
            product.inventory = int(inventory_input)
        except (ValueError, TypeError):
            product.inventory = 0
            flash('Invalid inventory value. Set to 0 by default.')
        db.session.commit()
        return redirect(url_for('admin_products'))
        product.image_url = request.form.get('image_url', '')
        product.inventory = int(request.form.get('inventory', 0))
        db.session.commit()
        return redirect(url_for('admin_products'))
    return render_template('edit_product.html', product=product)

# Home page route
@app.route('/', methods=['GET', 'POST'])
def home():
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    query = Product.query
    if search_query:
        query = query.filter(Product.name.ilike(f'%{search_query}%'))
    if category_filter:
        query = query.filter(Product.category == category_filter)
    products = query.all()
    categories = [c[0] for c in db.session.query(Product.category).distinct().all() if c[0]]
    return render_template('home.html', products=products, search_query=search_query, category_filter=category_filter, categories=categories)

# Admin product management page
@app.route('/admin_products')
def admin_products():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.username != 'admin':
        return redirect(url_for('login'))
    products = Product.query.all()
    return render_template('admin_products.html', products=products)

# Add product page (admin only)
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    if not user or user.username != 'admin':
        return redirect(url_for('login'))
    error = None
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        inventory = request.form.get('inventory')
        category = request.form.get('category')
        image_url = request.form.get('image_url', '')
        if not name or not price or not inventory:
            error = 'Name, price, and inventory are required.'
        else:
            try:
                price = float(price)
                inventory = int(inventory)
            except ValueError:
                error = 'Invalid price or inventory value.'
            if not error:
                product = Product(name=name, price=price, inventory=inventory, category=category, image_url=image_url)
                db.session.add(product)
                db.session.commit()
                return redirect(url_for('admin_products'))
    return render_template('add_product.html', error=error)



@app.route('/admin/product/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    user = User.query.get(session.get('user_id'))
    if not user or user.username != 'admin':
        return redirect(url_for('login'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_products'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            error = 'Username and password required'
        else:
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                return redirect(url_for('home'))
            error = 'Invalid credentials'
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            error = 'Username and password required'
        elif User.query.filter_by(username=username).first():
            error = 'Username already exists'
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product.html', product=product)


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    products = []
    total = 0
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            products.append({'name': product.name, 'price': product.price, 'image_url': product.image_url})
            total += product.price
    return render_template('cart.html', cart_items=cart_items, products=products, total=total)


@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    product = Product.query.get(product_id)
    if product:
        cart_count = Cart.query.filter_by(user_id=session['user_id'], product_id=product_id).count()
        if product.inventory > cart_count:
            cart_item = Cart(user_id=session['user_id'], product_id=product_id)
            db.session.add(cart_item)
            db.session.commit()
            return redirect(url_for('cart'))
        else:
            return render_template('product.html', product=product, error='Cannot add more items than available inventory.')
    return redirect(url_for('product_detail', product_id=product_id))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    products = []
    total = 0
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            products.append({'name': product.name, 'price': product.price, 'image_url': product.image_url})
            total += product.price
    if request.method == 'POST':
        # Stripe payment processing
        token = request.form.get('stripeToken')
        if not token:
            flash('Payment token missing.')
            return render_template('checkout.html', products=products, total=total, stripe_key=STRIPE_PUBLISHABLE_KEY)
        try:
            charge = stripe.Charge.create(
                amount=int(total * 100), # Stripe expects cents
                currency='usd',
                description='Ecommerce Purchase',
                source=token
            )
            for item in cart_items:
                product = Product.query.get(item.product_id)
                if product and product.inventory > 0:
                    product.inventory -= 1
                    db.session.delete(item)
            order = Order(user_id=session['user_id'])
            db.session.add(order)
            db.session.commit()
            # Email notification stub
            print(f"Order confirmation email sent to user {session['user_id']}")
            return render_template('checkout.html', success=True, products=products, total=total, stripe_key=STRIPE_PUBLISHABLE_KEY)
        except stripe.error.CardError:
            flash('Your card was declined.')
        except Exception as e:
            flash(f'Payment error: {str(e)}')
        return render_template('checkout.html', products=products, total=total, stripe_key=STRIPE_PUBLISHABLE_KEY)
    return render_template('checkout.html', products=products, total=total, stripe_key=STRIPE_PUBLISHABLE_KEY)

if __name__ == '__main__':
    app.run(debug=True)