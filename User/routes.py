from flask import Flask, request, render_template, redirect, url_for, session, flash, jsonify,send_from_directory
from flask_mysqldb import MySQL, MySQLdb
import secrets
import os
import bcrypt
from flask_mail import Mail, Message
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import base64
import numpy as np
import tensorflow as tf
from datetime import timedelta,datetime
from googleapiclient.discovery import build
import random


load_dotenv()  # Load environmental variables

app = Flask(__name__)

# Session data encryption
app.config['SECRET_KEY'] = secrets.token_hex(16)

# Set session timeout to 7 days
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Configure flask mail
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='music.recommendations24@gmail.com',
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    MAIL_DEBUG=True,
    MAIL_DEFAULT_SENDER='music.recommendations24@gmail.com'
)

mail = Mail(app)

# Configure MySQL
app.config.update(
    MYSQL_HOST='localhost',
    MYSQL_USER='root',
    MYSQL_PASSWORD='',
    MYSQL_DB='music_db'
)

mysql = MySQL(app)

# Load the emotion detection model
model_path = os.path.join('Trained model', 'model_trained_file_1.h5')
model = tf.keras.models.load_model(model_path)

# Define emotion labels
emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprised']

youtube_api_keys = ['YOUTUBE_API_KEY']
current_key_index = 0

# Initialize YouTube Data API client
def get_youtube_service(api_key):
    return build('youtube', 'v3', developerKey=api_key)

def send_email(subject, recipient, html_body):
    message = Message(subject, recipients=[recipient], html=html_body)
    mail.send(message)

def generate_confirmation_code():
    return ''.join(random.choices('0123456789', k=6))

def preprocess_image(image):
    image = image.convert('L')  
    image = image.resize((48, 48))  
    image_array = np.array(image)  
    image_array = image_array / 255.0  
    image_array = image_array.reshape(1, 48, 48, 1)  
    return image_array

def get_songs_by_mood(mood):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT name, artist, genre FROM song WHERE mood = %s", (mood,))
    songs = cursor.fetchall()
    cursor.close()
    return songs

def fetch_youtube_link(song_name, artist_name):
    global current_key_index
    for attempt in range(len(youtube_api_keys)):
        try:
            youtube = get_youtube_service(youtube_api_keys[current_key_index])
            search_response = youtube.search().list(
                q=f"{song_name} {artist_name} official video",
                part='id',
                maxResults=1
            ).execute()

            if search_response['items']:
                video_id = search_response['items'][0]['id']['videoId']
                youtube_link = f"https://www.youtube.com/watch?v={video_id}"
            else:
                youtube_link = "No video found"
                
            return youtube_link

        except Exception as e:
            print(f"Error with API key {current_key_index + 1}: {e}")
            # Switch to the next key if an error occurs
            current_key_index = (current_key_index + 1) % len(youtube_api_keys)
    return "Quota exceeded for all keys"

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['Email']
        dob = request.form['dob']
        plaintext_password = request.form['password']
        hashed_password = bcrypt.hashpw(plaintext_password.encode('utf-8'), bcrypt.gensalt())

        confirmation_code = generate_confirmation_code()
        code_generated_at = datetime.now()

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO users(name, email, dob, password, role, confirmation_code, code_generated_at) 
            VALUES (%s, %s, %s, %s, 'user', %s, %s)
            """, (username, email, dob, hashed_password, confirmation_code, code_generated_at))
        mysql.connection.commit()

        subject = "Your confirmation code"
        html = render_template('email_confirmation.html', confirmation_code=confirmation_code)
        send_email(subject, email, html)

        flash('A confirmation code has been sent to your email. Please check to confirm.', 'success')
        return redirect(url_for('confirm_code', email=email))
    
    return render_template('registration.html')

@app.route('/confirm_code', methods=['GET', 'POST'])
def confirm_code():
    email = request.args.get('email')
    remaining_time = 120
    
    if request.method == 'POST':
        email = request.form['Email']
        code = request.form['code']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        if user:
            if user['confirmation_code'] == code and datetime.now() - user['code_generated_at'] < timedelta(minutes=10):
                cursor.execute('UPDATE users SET confirmed = %s WHERE email = %s', (True, email))
                mysql.connection.commit()
                cursor.close()
                
                session['logged_in'] = True
                session['user_id'] = user['id']
                session['username'] = user['name']
                
                flash('Email confirmed. You are now logged in.', 'success')
                return redirect(url_for('detect'))
            else:
                flash('Invalid or expired confirmation code.', 'error')
        else:
            flash('User does not exist.', 'error')
    if email:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            time_since_last_code = datetime.now() - user['code_generated_at']
            remaining_time = int(max(0, (timedelta(minutes=2) - time_since_last_code).total_seconds()))
    return render_template('confirm_code.html', email=email, remaining_time=remaining_time)

@app.route('/resend_code', methods=['POST'])
def resend_code():
    email = request.form['Email']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
    user = cursor.fetchone()
    
    if user:
        time_since_last_code = datetime.now() - user['code_generated_at']
        if time_since_last_code > timedelta(minutes=2):
            confirmation_code = generate_confirmation_code()
            code_generated_at = datetime.now()
            cursor.execute('UPDATE users SET confirmation_code = %s, code_generated_at = %s WHERE email = %s', (confirmation_code, code_generated_at, email))
            mysql.connection.commit()
            
            subject = "Your new confirmation code"
            html = render_template('email_confirmation.html', confirmation_code=confirmation_code)
            send_email(subject, email, html)
            
            flash('A new confirmation code has been sent to your email.', 'success')
        else:
            flash('You can only resend the code after 2 minutes.', 'error')
    else:
        flash('User does not exist.', 'error')
    
    cursor.close()
    return redirect(url_for('confirm_code', email=email))

@app.route('/userlogin', methods=['GET', 'POST'])
def userlogin():
    if 'logged_in' in session:
        return redirect(url_for('detect'))
    
    if request.method == 'POST':
        email = request.form['Email']
        plaintext_password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        
        if user and bcrypt.checkpw(plaintext_password.encode('utf-8'), user['password'].encode('utf-8')):
            if user['confirmed']:
                session['logged_in'] = True
                session['user_id'] = user['id']
                session['username'] = user['name']
                
                session.permanent = True
                return redirect(url_for('detect'))
            else:
                flash('Please confirm your email address to log in.', 'error')
                return redirect(url_for('userlogin'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('userlogin'))
    
    return render_template('userlogin.html')

@app.route('/detect')
def detect():
    if 'logged_in' not in session:
        flash('You must log in first.', 'error')
        return redirect(url_for('userlogin'))
    return render_template('detect.html')

@app.route('/process_frames', methods=['POST'])
def process_frames():
    if 'logged_in' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'})
    
    try:
        frame_data = request.get_json()['frame']
        frame_image = Image.open(BytesIO(base64.b64decode(frame_data.split(',')[1])))
        processed_frame = preprocess_image(frame_image)
        prediction = model.predict(processed_frame)
        emotion_index = np.argmax(prediction)
        detected_emotion = emotion_labels[emotion_index]

        songs = get_songs_by_mood(detected_emotion)

        suggested_songs = []
        for song in songs:
            youtube_link = fetch_youtube_link(song['name'], song['artist'])
            suggested_songs.append({
                'song_name': song['name'],
                'artist': song['artist'],
                'genre': song['genre'],
                'youtube_link': youtube_link
            })

        session['suggested_songs'] = suggested_songs
        session['detected_emotion'] = detected_emotion

        return jsonify({'status': 'success'})
    
    except Exception as e:
        flash(f'Error processing frame: {str(e)}', 'error')
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/recommendations')
def recommendations():
    if 'logged_in' not in session:
        flash('You must log in first.', 'error')
        return redirect(url_for('userlogin'))
    
    songs = session.get('suggested_songs', [])
    emotion = session.get('detected_emotion', 'No emotion detected')
    return render_template('process_frames.html', suggested_songs=songs, detected_emotion=emotion)

@app.route('/get_camera_access_preference')
def get_camera_access_preference():
    if 'logged_in' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'})

    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT camera_access FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()

    return jsonify({'status': 'success', 'camera_access': user['camera_access']})

@app.route('/camera_access', methods=['POST'])
def camera_access():
    if 'logged_in' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'})

    data = request.get_json()
    camera_access = data['camera_access']
    user_id = session['user_id']

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE users SET camera_access = %s WHERE id = %s', (camera_access, user_id))
    mysql.connection.commit()
    cursor.close()

    return jsonify({'status': 'success'})

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('userlogin'))

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'Logo.png', mimetype='image/png')


if __name__ == '__main__':
    app.run(debug=True)
