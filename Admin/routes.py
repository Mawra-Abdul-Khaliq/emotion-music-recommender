from flask import Flask, request, flash, render_template, redirect, url_for, session, send_from_directory
from flask_mysqldb import MySQL
import bcrypt
import MySQLdb.cursors
import secrets 
import os
from dotenv import load_dotenv

load_dotenv()  # Load environmental variable

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a random secret key

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'music_db'

mysql = MySQL(app)

@app.route('/')
def admin():
    return render_template('adminlogin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('admin'))

@app.route('/setadmin')
def set_admin():
    admin_username = 'Mawra'
    admin_email = 'mawrakhaliq1@gmail.com'
    admin_age = 22
    admin_password = os.environ.get('admin_password')
    try:
        if not is_admin_exists():
            cursor = mysql.connection.cursor()
            hashed_admin_password = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("INSERT INTO users (name, email, age, password, confirmed, role) VALUES(%s, %s, %s, %s, True, 'admin')",
                           (admin_username, admin_email, admin_age, hashed_admin_password))
            mysql.connection.commit()
            cursor.close()
            return 'Admin user added successfully!'
        else:
            return 'Admin user already exists!'
    except Exception as e:
        return f'An error occurred: {str(e)}'

def is_admin_exists():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    count = cursor.fetchone()[0]
    cursor.close()
    return count > 0

@app.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['Email']
        plain_text_password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('SELECT * FROM users WHERE email = %s AND role = "admin"', (email,))
        
        admin = cursor.fetchone()
        cursor.close()

        if admin and bcrypt.checkpw(plain_text_password.encode('utf-8'), admin['password'].encode('utf-8')):
            session['logged_in'] = True
            session['user_id'] = admin['id']
            session['username'] = admin['name']
            return redirect(url_for('adminpage'))
        else:
             flash("Incorrect Email or Password")
             return redirect(url_for('admin_login')) 
    return render_template('adminlogin.html')

@app.route('/adminpage')
def adminpage():
    if 'logged_in' in session:
        return redirect(url_for('Index'))
    else:
        return redirect(url_for('admin'))

@app.route('/Index')
def Index():
    if 'logged_in' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM song")
        data = cur.fetchall()

        cur.execute("SELECT DISTINCT genre FROM song")
        genres = cur.fetchall()

        cur.execute("SELECT DISTINCT mood FROM song")
        moods = cur.fetchall()

        cur.close()
        return render_template("edit.html", song=data, genres=genres, moods=moods)
    else:
        return redirect(url_for('admin'))

@app.route('/add_data', methods=['POST'])
def add_data():
    if 'logged_in' in session:
        if request.method == "POST":
            name = request.form['name']
            artist = request.form['artist']
            genre = request.form['genre']
            mood = request.form['mood']

            if genre == "other":
                genre = request.form['new_genre']

            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO song(name, artist, genre, mood) VALUES (%s, %s, %s, %s)", (name, artist, genre, mood))
            
            mysql.connection.commit()
            cur.close()
        flash("Successfully add new data")
        return redirect(url_for('Index'))
    else:
        return redirect(url_for('admin'))

@app.route('/update', methods=['POST'])
def update():
   if 'logged_in' in session:
        if request.method == "POST":
            id_song = request.form['id']
            name = request.form['name']
            artist = request.form['artist']
            genre = request.form['genre']
             # Use the new genre if the "other" option was selected
            if genre == "other":
                genre = request.form.get('new_genre', genre)
            mood = request.form['mood']
            cur = mysql.connection.cursor()
            cur.execute("""
            UPDATE song
            SET name=%s, artist=%s, genre=%s, mood=%s
            WHERE id=%s
            """, (name, artist, genre, mood, id_song))
            mysql.connection.commit()
            flash("Successfully Update data")
        return redirect(url_for('Index'))
   else:
        return redirect(url_for('admin'))

@app.route('/delete/<string:id_song>', methods=['GET'])
def delete(id_song):
    if 'logged_in' in session:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM song WHERE id=%s", (id_song,))
        mysql.connection.commit()
        flash("Successfully delete data")
        return redirect(url_for('Index'))
    else:
        return redirect(url_for('admin'))
    
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'Logo.png', mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, port=5001)