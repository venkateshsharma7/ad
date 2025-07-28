from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
import os
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta

# === Flask and Upload Config ===
app = Flask(__name__)
app.secret_key = "your_secret_key_here"
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === MongoDB Setup (Your URI) ===
MONGO_URI = 'mongodb+srv://sharmavenkat765:Vh1vXfKkQPWAj0Dx@cluster0.kkexheb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client['annadaatha']

try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

# === Login Required Decorator ===
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Login required!')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# === Routes ===

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

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
        else:
            flash("Invalid document type! Please upload PNG, JPG, JPEG, or PDF.")
            return redirect(request.url)

        db.users.insert_one({
            'role': role,
            'name': name,
            'email': email,
            'password': password,   # For real use, hash this!
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
            flash('Login successful!')
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
    if role == 'donor':
        return render_template('donor_dashboard.html', name=name)
    elif role == 'recipient':
        return render_template('recipient_dashboard.html', name=name)
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
        photo_file = request.files.get('photo')
        photo_filename = None

        if photo_file and photo_file.filename:
            if allowed_file(photo_file.filename):
                photo_filename = "food_" + secure_filename(photo_file.filename)
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
                photo_file.save(photo_path)
            else:
                flash("Invalid image file type (must be PNG/JPG/JPEG).")
                return redirect(request.url)

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

if __name__ == '__main__':
    app.run(debug=True)
