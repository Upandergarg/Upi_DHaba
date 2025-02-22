from flask import Flask, render_template, redirect, url_for, request, flash,jsonify,session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy.orm import joinedload
from functools import wraps
from datetime import datetime

import requests
import os

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"
UNSPLASH_ACCESS_KEY = "ZHIJbZdKPiPucflaNNgtvW0UQvv97NZhhqmyiseTxRM"


def get_food_image(food_name):
    url = f"https://api.unsplash.com/search/photos?query={food_name}+food&client_id={UNSPLASH_ACCESS_KEY}&per_page=1"
    response = requests.get(url).json()
    
    if response["results"]:
        return response["results"][0]["urls"]["regular"]  
    return "https://via.placeholder.com/400x300.png?text=No+Image" 


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = "login"

class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  
    email = db.Column(db.String(100), unique=True, nullable=False)
    address= db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)  
    city = db.Column(db.String(15), nullable=False)  
    role = db.Column(db.String(10), nullable=False, default="user")

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)
    
class Restaurant(db.Model):
    __tablename__="restaurants"

    rid=db.Column(db.Integer, primary_key=True)
    rname= db.Column(db.String(50),nullable=False)
    raddress = db.Column(db.String(100),nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)

class MenuItem(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    restaurant_id = db.Column(
        db.Integer, 
        db.ForeignKey('restaurants.rid', ondelete="CASCADE"), 
        nullable=False
    )
    restaurant = db.relationship('Restaurant', backref=db.backref('menu_items', lazy=True))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship("User", backref="orders")  
    order_items = db.relationship('OrderItem', backref='order', lazy=True)
    
    @property
    def total_price(self):
        return sum(item.quantity * item.price for item in self.order_items)





class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
   
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    menu_item = db.relationship("MenuItem", backref="order_items")  


   

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False) 
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    menu_item = db.relationship("MenuItem", backref="cart_items")  

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User,int(user_id))

with app.app_context():
    db.create_all()

@app.route('/check_mobile', methods=['POST'])
def check_mobile():
    data = request.get_json()
    mobile = data.get('mobile')

    
    user = User.query.filter_by(mobile=mobile).first()
    if user:
        return jsonify({'exists': True})  
    else:
        return jsonify({'exists': False})  

@app.route('/login_mobile', methods=['GET','POST'])
def login_mobile():
    if request.method=="POST":
     mobile = request.form.get('mobile_login')
     password = request.form.get('password')
     user = User.query.filter_by(mobile=mobile).first()
     if not user:
         return "Mobile number does not exist!", 400

     
     if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
     else:
      flash("Invalid password.", "danger")
      return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("user_dashboard2"))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        address=request.form.get("address")
        confirm_password = request.form.get("confirm_password")
        mobile = request.form.get("mobile")
        role=request.form.get("role")
        city=request.form.get("city")

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("signup"))

        if User.query.filter_by(email=email).first():
            flash("Email already exists!", "danger")
            return redirect(url_for("signup"))

        new_user = User(name=name, email=email, mobile=mobile,role=role,address=address,city=city)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

def admin_required(func):
    @wraps(func)
    @login_required  
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Access denied!", "danger")
            return redirect(url_for('user_dashboard'))
        return func(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/about_us")
def about_us():
    return render_template("about_us.html")

@app.route("/best_seller")
def best_seller():
    return render_template("bestseller.html")

@app.route("/admin_dashboard")
@admin_required
@login_required
def admin_dashboard():
    user = User.query.filter_by(email=current_user.email).first()
    if current_user.role != "admin":
        flash("Unauthorized access!", "danger")
        return redirect(url_for("login")) 

    return render_template("dashboardadmin.html",mail=user.email)

@app.route('/delete_restaurant/<int:rid>', methods=['POST'])
@admin_required
@login_required
def delete_restaurant(rid):
    restaurant = Restaurant.query.get_or_404(rid)

    MenuItem.query.filter_by(restaurant_id=rid).delete()

  
    if restaurant.image_filename:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], restaurant.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(restaurant)
    db.session.commit()
    
    flash('Restaurant deleted successfully!', 'success')
    return redirect(url_for('user_dashboard'))


@app.route('/edit_restaurant/<int:rid>', methods=['GET'])
@admin_required
def edit_restaurant(rid):
    restaurant = Restaurant.query.get_or_404(rid)
    return render_template('add_restaurant.html', restaurant=restaurant)


@app.route("/user_dashboard")
@login_required
def user_dashboard():
    user_city = current_user.city  
    restaurants = Restaurant.query.filter(Restaurant.raddress.ilike(f"%{user_city}%")).all()  
    return render_template("user_dashboard.html", restaurants=restaurants)

@app.route('/submit_restaurant', methods=['POST'])
@admin_required
def submit_restaurant():
    rid = request.form.get('rid')  
    rname = request.form['restaurant_name']
    raddress = request.form['restaurant_address']
    
    image = request.files['restaurant_image']
    
    if rid: 
        restaurant = Restaurant.query.get_or_404(rid)
        restaurant.rname = rname
        restaurant.raddress = raddress
        
        if image: 
            old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], restaurant.image_filename)
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
            
            image_filename = image.filename
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            restaurant.image_filename = image_filename
        
        flash('Restaurant updated successfully!', 'success')
    else:  
        image_filename = image.filename if image else None
        if image:
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        restaurant = Restaurant(rname=rname, raddress=raddress, image_filename=image_filename)
        db.session.add(restaurant)
        flash('Restaurant added successfully!', 'success')

    db.session.commit()
    return redirect(url_for('add_restaurant'))

@app.route('/admin_dashboard/add_restaurant')
@admin_required
@login_required
def add_restaurant():
    return render_template('add_restaurant.html')


@app.route('/menu/<int:restaurant_id>')
@login_required
def view_menu(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()

    
    for item in menu_items:
        item.image_url = get_food_image(item.name)

    return render_template("menu.html", restaurant=restaurant, menu_items=menu_items)


@app.route('/menu/edit/<int:restaurant_id>', methods=['GET', 'POST'])
@admin_required
def edit_menu(restaurant_id):
    if current_user.role != 'admin':
        flash("You are not authorized!", "danger")
        return redirect(url_for('view_menu', restaurant_id=restaurant_id))

    restaurant = Restaurant.query.get_or_404(restaurant_id)

    if request.method == 'POST':
        item_name = request.form['item_name']
        price = request.form['price']
        new_item = MenuItem(name=item_name, price=price, restaurant_id=restaurant_id)
        db.session.add(new_item)
        db.session.commit()
        flash("Menu item added!", "success")
        return redirect(url_for('edit_menu', restaurant_id=restaurant_id))

    menu_items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
    return render_template('edit_menu.html', restaurant=restaurant, menu_items=menu_items)

@app.route('/update_menu_item/<int:item_id>', methods=['POST'])
@admin_required
def update_menu_item(item_id):
    item = MenuItem.query.get_or_404(item_id)
    
    item.name = request.form['item_name']
    item.price = request.form['price']

    db.session.commit()
    flash("Menu item updated successfully!", "success")

    return redirect(url_for('edit_menu', restaurant_id=item.restaurant_id))

@app.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    
    total_price = sum(item.quantity * item.menu_item.price for item in cart_items if item.menu_item)

    return render_template("cart.html", cart_items=cart_items, total_price=total_price)


@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    item = Cart.query.get_or_404(item_id)
    
    if item.user_id != current_user.id:
        flash("Unauthorized action!", "danger")
        return redirect(url_for('cart'))

    db.session.delete(item)
    db.session.commit()

    flash("Item removed from cart!", "success")
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        flash("Your cart is empty!", "danger")
        return redirect(url_for('cart'))

    
    new_order = Order(
        user_id=current_user.id,
        status="Pending",
        timestamp=datetime.utcnow()
    )
    db.session.add(new_order)
    db.session.commit()  


    for item in cart_items:
        for _ in range(item.quantity):  
            order_item = OrderItem(
                order_id=new_order.id,
                menu_item_id=item.item_id,  
                name=item.name,  
                price=item.price,  
                quantity=1  
            )
            db.session.add(order_item)

  
    Cart.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    flash("Order placed successfully!", "success")
    return redirect(url_for('my_orders'))



@app.route('/change_address', methods=['POST'])
@login_required
def change_address():
    new_address = request.form.get('new_address')
    if new_address:
        current_user.address = new_address  
        db.session.commit() 
        flash('Address updated successfully!', 'success')
    else:
        flash('Please enter a valid address.', 'danger')

    return redirect(url_for('user_dashboard'))  


@app.route('/admin_dashboard/orders')
@admin_required
@login_required
def orders_admin():
    orders = Order.query.options(joinedload(Order.order_items).joinedload(OrderItem.menu_item)).all()
    return render_template("orders_admin.html", orders=orders)
    
@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))  

    if not item_id or quantity <= 0:
        flash("Invalid item or quantity!", "danger")
        return redirect(url_for('user_dashboard'))

    # Fetch the menu item from database
    menu_item = MenuItem.query.get(item_id)
    if not menu_item:
        flash("Menu item not found!", "danger")
        return redirect(url_for('user_dashboard'))

   
    existing_cart_item = Cart.query.filter_by(user_id=current_user.id, item_id=item_id).first()

    if existing_cart_item:
        existing_cart_item.quantity = min(5, existing_cart_item.quantity + quantity)  
    else:
        
        new_cart_item = Cart(
            user_id=current_user.id,
            item_id=menu_item.id,
            name=menu_item.name,
            price=menu_item.price,
            quantity=quantity
        )
        db.session.add(new_cart_item)

    db.session.commit()
    flash(f"{menu_item.name} added to cart!", "success")
    return redirect(url_for('view_menu', restaurant_id=menu_item.restaurant_id))

@app.route('/update_order_status/<int:order_id>', methods=['POST'])
@admin_required
@login_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")

    if new_status not in ["Pending", "Accepted", "Being Prepared", "Out for Delivery", "Delivered"]:
        flash("Invalid status!", "danger")
        return redirect(url_for('orders_admin'))

    order.status = new_status
    db.session.commit()

    flash("Order status updated successfully!", "success")
    return redirect(url_for('orders_admin'))

@app.route('/my_orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).all()  
    return render_template("my_orders.html", orders=orders)


@app.route('/order_details/<int:order_id>')
@login_required
def order_details(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    order_data = {
        'id': order.id,
        'user': order.user.name,
        'status': order.status,
        'total_price': order.total_price,
        'items': [
            {'name': item.menu_item.name, 'quantity': item.quantity, 'price': item.price}
            for item in order.order_items
        ]
    }
    return jsonify(order_data)

@app.route('/update_cart/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    new_quantity = request.form.get('quantity', type=int)

    if new_quantity is None or new_quantity < 1:
        flash("Quantity must be at least 1.", "warning")
    elif new_quantity > 5:
        flash("You can't add more than 5 of the same item.", "warning")
    else:
        cart_item = Cart.query.filter_by(id=item_id, user_id=current_user.id).first()
        if cart_item:
            cart_item.quantity = new_quantity
            db.session.commit()
            flash("Cart updated successfully!", "success")
        else:
            flash("Item not found in cart.", "danger")

    return redirect(url_for('cart'))

@app.route("/user_dashboard2")
@login_required
def user_dashboard2():
    return render_template("kfc.html")

if __name__ == "__main__":
    app.run(debug=True)
