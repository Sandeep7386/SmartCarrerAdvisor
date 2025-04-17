import pickle
import numpy as np
import logging
import pymysql
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Set up logging
logging.basicConfig(level=logging.INFO)

# Base directory for consistent file loading
base_dir = os.path.abspath(os.path.dirname(__file__))

# Load ML components

try:
    model = pickle.load(open(os.path.join(base_dir, "model.pkl"), "rb"))
    scaler = pickle.load(open(os.path.join(base_dir, "scaler.pkl"), "rb"))
    label_encoder = pickle.load(open(os.path.join(base_dir, "label_encoder.pkl"), "rb"))
    logging.info("Model, Scaler, and Label Encoder loaded successfully.")
except Exception as e:
    logging.error(f"Error loading ML components: {e}")
    model, scaler, label_encoder = None, None, None

# Database connection
conn = pymysql.connect(host='localhost', user='root', password='password', database='career_recommendation')
cursor = conn.cursor()

# Define routes below (rest of your Flask routes remain unchanged)

# Home page
@app.route('/')
def home():
    return render_template('career.html')

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
        conn.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('home'))
        else:
            return "Invalid credentials. Please try again."
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Forgot password page
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        # Logic for sending reset email can be implemented here
        return "Password reset link sent to your email. (Functionality placeholder)"
    return render_template('forgot-password.html')

# Job list page
@app.route('/job_list')
def job_list():
    return render_template('job_list.html')

# Dynamic job details
@app.route('/job_details/', defaults={'job_role': 'software-engineer'})
@app.route('/job_details/<job_role>')
def job_details(job_role):
    return render_template('job_details.html', job_role=job_role)

# Job description page
@app.route('/job_description')
def job_description():
    return render_template('description.html')

@app.route('/about')
def about():
    return render_template('about.html')

# Input form for prediction
@app.route('/input')
def input_page():
    return render_template('input.html')

# Prediction route with database saving
@app.route('/predict', methods=['POST'])
def predict():
    if model is None or scaler is None or label_encoder is None:
        return "Error: ML components failed to load."

    try:
        feature_names = [
            "Academic percentage in Operating Systems",
            "Percentage in Algorithms",
            "Percentage in Programming Concepts",
            "Percentage in Software Engineering",
            "Percentage in Computer Networks",
            "Percentage in Electronics Subjects",
            "Percentage in Computer Architecture",
            "Percentage in Mathematics",
            "Percentage in Communication skills",
            "Hours working per day",
            "Logical quotient rating",
            "Hackathons",
            "Coding skills rating",
            "Public speaking points",
            "Can work long time before system?",
            "Self-learning capability?",
            "Extra-courses did",
            "Certifications",
            "Workshops",
            "Interested subjects",
            "Interested career area",
            "Job/Higher Studies?",
            "Type of company want to settle in?",
            "Management or Technical",
            "Worked in teams ever?"
        ]

        features = []
        for feature in feature_names:
            features.append(float(request.form.get(feature, 0)))

        input_array = np.array(features).reshape(1, -1)
        input_scaled = scaler.transform(input_array)

        probabilities = model.predict_proba(input_scaled)[0]
        all_jobs = label_encoder.inverse_transform(np.arange(len(probabilities)))
        prediction_list = list(zip(all_jobs, probabilities))
        prediction_list.sort(key=lambda x: x[1], reverse=True)
        top_predictions = [job for job, prob in prediction_list[:3]]

        # Save prediction if user is logged in
        if 'user_id' in session:
            user_id = session['user_id']
            cursor.execute("""
                INSERT INTO predictions (user_id, os_percentage, algo_percentage, programming_percentage, networks_percentage, communication, logical_rating, coding_skills, interested_subjects, interested_career, prediction_result)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (user_id, features[0], features[1], features[2], features[4], features[8], features[10], features[12], request.form['Interested subjects'], request.form['Interested career area'], top_predictions[0])
            )
            conn.commit()

        return render_template('prediction.html', predicted_jobs=top_predictions)

    except Exception as e:
        logging.error(f"Prediction error: {e}")
        return f"Error during prediction: {str(e)}"

# Profile page
@app.route('/profile')
def profile():
    if 'user_id' in session:
        cursor.execute("SELECT prediction_result, interested_subjects, interested_career, created_at FROM predictions WHERE user_id=%s ORDER BY created_at DESC", (session['user_id'],))
        history = cursor.fetchall()
        return render_template('profile.html', username=session['username'], history=history)
    return redirect(url_for('login'))

# Statistics page
@app.route('/statistics')
def statistics():
    career = request.args.get('career', 'Software Developer')
    return render_template('statistics.html', career=career)

# Dummy statistics API
@app.route('/api/statistics_data', methods=['POST'])
def statistics_data():
    data = request.get_json()
    top_career = data.get('career', 'Software Developer')

    prediction_data = [
        {'career': 'Software Developer', 'confidence': 90},
        {'career': 'Database Developer', 'confidence': 85},
        {'career': 'UX Designer', 'confidence': 80},
        {'career': 'Data Architect', 'confidence': 75},
        {'career': 'Network Engineer', 'confidence': 70}
    ]

    missing_skills = ['Leadership', 'System Design', 'Cloud Knowledge']
    companies = [
        {'name': 'Google', 'link': 'https://careers.google.com'},
        {'name': 'Microsoft', 'link': 'https://careers.microsoft.com'},
        {'name': 'Amazon', 'link': 'https://www.amazon.jobs'}
    ]
    roadmap_steps = [
        "Learn core programming languages",
        "Work on projects",
        "Contribute to open source",
        "Learn system design",
        "Prepare for interviews"
    ]

    return jsonify({
        'predictions': prediction_data,
        'missing_skills': missing_skills,
        'companies': companies,
        'roadmap': roadmap_steps
    })

if __name__ == '__main__':
    app.run(debug=True)
