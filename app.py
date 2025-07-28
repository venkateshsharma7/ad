from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
import os
from werkzeug.utils import secure_filename

# === Flask Configuration ===
app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Needed for flash messages (you can change this)

# === File Upload Configuration ===
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === MongoDB Configuration ===
MONGO_URI = 'mongodb+srv://sharmavenkat765:Vh1vXfKkQPWAj0Dx@cluster0.kkexheb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client['annadaatha']  # Your DB name

# Test connection on startup
try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

# === Routes ===

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form['role']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        file = request.files['kyc']

        # Validate KYC file
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
        else:
            flash("Invalid document type! Please upload PNG, JPG, JPEG, or PDF.")
            return redirect(request.url)

        # Store the user in MongoDB
        user = {
            'role': role,
            'name': name,
            'email': email,
            'password': password,  # NOTE: For real use, always hash passwords!
            'kyc_file': filename,
            'status': 'pending'    # To be reviewed by admin
        }
        db.users.insert_one(user)
        flash("Registration successful! Please wait for admin approval.")
        return redirect(url_for('home'))
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)
