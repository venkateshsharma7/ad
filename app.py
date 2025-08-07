from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from functools import wraps
from datetime import datetime, timedelta
from bson.objectid import ObjectId
import os
import requests

# ==== CONFIG ====
app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # CHANGE this for production!

ADMIN_EMAILS = {'vkrsharma1976@gmail.com'}
UPLOAD_FOLDER = os.path.join('static', 'uploads')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Unsplash API Access Key (replace with your own)
UNSPLASH_ACCESS_KEY = "PAqKqdFq2W9KgIu04skiiNGE4XWRkNCJHrYWqHStYMg"

MONGO_URI = 'mongodb+srv://sharmavenkat765:Vh1vXfKkQPWAj0Dx@cluster0.kkexheb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client['annadaatha']

@app.context_processor
def inject_admin_emails():
    return dict(ADMIN_EMAILS=ADMIN_EMAILS)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Login required!')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('email') not in ADMIN_EMAILS:
            flash('Admin access required!')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def download_unsplash_image(food_name, save_dir=UPLOAD_FOLDER, access_key=UNSPLASH_ACCESS_KEY):
    """Fetch the best Unsplash image URL for food_name and save image locally, return filename."""
    query = food_name.strip() + ' food'
    url = 'https://api.unsplash.com/search/photos'
    params = {
        'query': query,
        'client_id': access_key,
        'per_page': 1,
        'orientation': 'landscape'
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
        results = data.get('results', [])
        if not results:
            return None
        image_url = results[0]['urls']['regular']
        # Normalize filename: only alphanumeric + underscore, lowercase
        safe_name = ''.join(c for c in food_name.lower() if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        filename = f"{safe_name}.jpg"
        filepath = os.path.join(save_dir, filename)
        # Download image only if it doesn't already exist
        if not os.path.exists(filepath):
            img_data = requests.get(image_url).content
            with open(filepath, 'wb') as f:
                f.write(img_data)
        return filename
    except Exception as e:
        print(f"Unsplash API/download error: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        file = request.files.get('kyc')
        if file and '.' in file.filename:
            filename = file.filename
            upload_dir = os.path.join('static', 'uploads')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            file.save(os.path.join(upload_dir, filename))
        else:
            flash("Invalid document type! Please upload a valid KYC document.")
            return redirect(request.url)
        db.users.insert_one({
            'role': role,
            'name': name,
            'email': email,
            'password': password,  # IMPORTANT: Hash passwords in production!
            'kyc_file': filename,
            'status': 'pending'
        })
        flash("Registration successful! Please wait for admin approval.")
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.users.find_one({'email': email, 'password': password})
        if user:
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            session['name'] = user['name']
            session['email'] = user['email']
            flash('Login successful!')
            if email in ADMIN_EMAILS:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password. Please try again.')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    name = session.get('name')
    email = session.get('email')
    if email in ADMIN_EMAILS:
        return redirect(url_for('admin_dashboard'))
    if role == 'donor':
        donated_foods = list(db.food.find({'donor_id': session['user_id']}).sort('timestamp', -1))
        return render_template('donor_dashboard.html', name=name, donated_foods=donated_foods)
    elif role == 'recipient':
        my_orders = list(db.food.find({'requested_by': session['user_id']}).sort('requested_at', -1))
        return render_template('recipient_dashboard.html', name=name, my_orders=my_orders)
    else:
        flash('Unknown role.')
        return redirect(url_for('logout'))

@app.route('/donate_food', methods=['GET', 'POST'])
@login_required
def donate_food():
    if session.get('role') != 'donor':
        flash("Only donors can donate food.")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        food_name = request.form.get('food_name')
        description = request.form.get('description')
        quantity = request.form.get('quantity')
        expiry_hours = int(request.form.get('expiry_hours'))
        donor_id = session.get('user_id')

        # Download Unsplash image, fallback to default if fails
        photo_filename = download_unsplash_image(food_name) or "default.jpg"
        expiry_time = datetime.utcnow() + timedelta(hours=expiry_hours)

        food_doc = {
            'food_name': food_name,
            'description': description,
            'quantity': quantity,
            'donor_id': donor_id,
            'photo': photo_filename,
            'expiry_time': expiry_time,
            'status': 'pending',
            'timestamp': datetime.utcnow()
        }
        db.food.insert_one(food_doc)
        flash("Food donation submitted! Awaiting admin approval.")
        return redirect(url_for('dashboard'))

    return render_template('donate_food.html')

@app.route('/browse_food')
@login_required
def browse_food():
    if session.get('role') != 'recipient':
        flash('Only recipients can browse food.')
        return redirect(url_for('dashboard'))

    now = datetime.utcnow()
    foods = list(db.food.find({'status': 'approved', 'expiry_time': {'$gt': now}}).sort('timestamp', -1))

    # Build image URL for each food, fallback to default.jpg if file missing
    for food in foods:
        image_path = os.path.join(UPLOAD_FOLDER, food.get('photo', ''))
        if food.get('photo') and os.path.isfile(image_path):
            food['img_url'] = url_for('static', filename='uploads/' + food['photo'])
        else:
            food['img_url'] = url_for('static', filename='uploads/default.jpg')

    return render_template('browse_food.html', foods=foods)

# --- Order Food Route for Recipients ---

@app.route('/order_food/<food_id>', methods=['POST'])
@login_required
def order_food(food_id):
    if session.get('role') != 'recipient':
        flash('Only recipients can order food.')
        return redirect(url_for('dashboard'))

    recipient_id = session.get('user_id')

    updated = db.food.update_one(
        {'_id': ObjectId(food_id), 'status': 'approved'},
        {'$set': {
            'status': 'requested',
            'requested_by': recipient_id,
            'requested_at': datetime.utcnow()
        }}
    )

    if updated.modified_count == 1:
        flash('Food requested! Please wait for confirmation.')
    else:
        flash('Unable to request this food.')

    return redirect(url_for('browse_food'))

# --- Admin Routes ---

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    users = list(db.users.find({'status': 'pending'}))
    foods = list(db.food.find({'status': {'$in': ['pending', 'requested']}}))

    for food in foods:
        image_path = os.path.join(UPLOAD_FOLDER, food.get('photo', ''))
        if food.get('photo') and os.path.isfile(image_path):
            food['img_url'] = url_for('static', filename='uploads/' + food['photo'])
        else:
            food['img_url'] = url_for('static', filename='uploads/default.jpg')

    return render_template('admin_dashboard.html', users=users, foods=foods)

@app.route('/admin/approve_user/<user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'status': 'approved'}})
    flash('User approved.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject_user/<user_id>', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    db.users.update_one({'_id': ObjectId(user_id)}, {'$set': {'status': 'rejected'}})
    flash('User rejected.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_food/<food_id>', methods=['POST'])
@login_required
@admin_required
def approve_food(food_id):
    db.food.update_one({'_id': ObjectId(food_id)}, {'$set': {'status': 'approved'}})
    flash('Food donation approved.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject_food/<food_id>', methods=['POST'])
@login_required
@admin_required
def reject_food(food_id):
    db.food.update_one({'_id': ObjectId(food_id)}, {'$set': {'status': 'rejected'}})
    flash('Food donation rejected.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/deliver_food/<food_id>', methods=['POST'])
@login_required
@admin_required
def mark_delivered(food_id):
    db.food.update_one({'_id': ObjectId(food_id)},
                       {'$set': {'status': 'delivered', 'delivered_at': datetime.utcnow()}})
    flash('Food marked as delivered.')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
