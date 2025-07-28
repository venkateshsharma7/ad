from flask import Flask, render_template
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = 'mongodb+srv://sharmavenkat765:Vh1vXfKkQPWAj0Dx@cluster0.kkexheb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)  # Set a timeout for faster failure
db = client['annadaatha']

try:
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
