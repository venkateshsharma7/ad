from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
import os
from werkzeug.utils import secure_filename

# === Configurations ===
app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Change to a strong key for production
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === MongoDB Setup ===
MONGO_URI = 'mongodb+srv://sharmavenkat765:Vh1vXfKkQPWAj0Dx@cluster0.kkexheb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client['annadaatha']

# Test connection
try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

# === ROUTES ===

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

        # Validate file
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
        else:
            flash("Invalid document type! Please upload PNG, JPG, JPEG, or PDF.")
            return redirect(request.url)

        # Store in MongoDB (do NOT use plain passwords for production apps!)
        db.users.insert_one({
            'role': role,
            'name': name,
            'email': email,
            'password': password,
            'kyc_file': filename,
            'status': 'pending'   # Awaiting admin approval
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
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password. Please try again.')
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
