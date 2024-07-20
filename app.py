from flask import Flask, render_template, request, redirect, url_for,session,flash,jsonify
import mysql.connector
from mysql.connector import Error
import openpyxl
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''
MYSQL_DB = 'search_engine'

users = {
    'user6': 'password6',
}


IMPORT_PASSWORD = '09062001'

@app.route('/')
def home():
    if 'role' in session:
        return render_template('index.html')
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            connection = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                sql = "SELECT * FROM users WHERE username = %s"
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
                
                if user:
                    if user['status'] == 0:
                        flash('User is inactive', 'danger')
                    elif user['active'] == 1:
                        flash('User is logged in another system', 'danger')
                    elif user['password'] == password:
                        session['username'] = user['username']
                        session['role'] = user['role']
                        session['id'] = user['id']
                        update_sql = "UPDATE users SET active = 1 WHERE username = %s"
                        cursor.execute(update_sql, (username,))
                        connection.commit()
                        flash('You were successfully logged in', 'success')
                        
                        if user['role'] == 'admin':
                            return redirect(url_for('home'))
                        else:
                            return redirect(url_for('search'))
                    else:
                        flash('Invalid credentials', 'danger')
                else:
                    flash('Invalid credentials', 'danger')
        
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
        finally:
            if 'connection' in locals():
                connection.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    try:
        if 'role' in session:
            username = session['username']
            
            # Connect to MySQL
            connection = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
            
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                
                # Update active status to 0 for logged-out user
                update_sql = "UPDATE users SET active = 0 WHERE username = %s"
                cursor.execute(update_sql, (username,))
                connection.commit()
                
                # Clear session variables
                session.pop('username', None)
                session.clear()
                
                flash('You were successfully logged out', 'success')
            else:
                flash('Error connecting to database', 'danger')
    except Error as e:
        flash(f"Error: {e}", 'danger')
    finally:
        if 'connection' in locals():
            connection.close()
    return redirect(url_for('home'))

@app.route('/protected')
def protected():
    if 'username' in session:
        return f"Hello, {session['username']}! This is a protected page."
    else:
        flash('You need to login first', 'warning')
        return redirect(url_for('login'))

app.config['SECRET_KEY'] = '123321'

def import_excel_to_mysql(excel_file, table_name):
    if 'role' in session and session['role'] == 'admin':
        try:
            # Open the Excel file
            workbook = openpyxl.load_workbook(excel_file)
            sheet = workbook.active
            connection = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
            if connection.is_connected():
                cursor = connection.cursor()
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS contacts (
                        ID VARCHAR(100) PRIMARY KEY,
                        firstname VARCHAR(100),
                        lastname VARCHAR(100),
                        dob DATE,
                        result VARCHAR(100)
                    )
                """)

                for row in sheet.iter_rows(min_row=2, values_only=True):  # Skip header row (assuming first row is header)
                    insert_query = f"""
                        INSERT IGNORE INTO {table_name} (ID, firstname, lastname, dob, result,type)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, row)

                connection.commit()
                return True

        except Error as e:
            print(f"Error: {e}")
            return False

        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()
                
    return render_template('login.html')
def search_in_mysql(query, firstname, lastname, dob,type_):
    if 'role' in session:
        try:
            connection = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )

            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                cursor.execute(f"SELECT * FROM contacts WHERE ID = '{query}'")
                results = cursor.fetchall()
                if not results:
                    sql = """
                        INSERT IGNORE INTO user_contacts (ID, firstname, lastname, dob, result,type)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (query, firstname, lastname, dob, 'result',type_))
                    connection.commit()

                return results

        except Error as e:
            print(f"Error: {e}")
            return None

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return render_template('login.html')
# # Route to home page
# @app.route('/')
# def home():
#     return render_template('index.html')


@app.route('/import', methods=['GET', 'POST'])
def import_data():
    if 'role' in session and session['role'] == 'admin':
        if request.method == 'POST':
            password_attempt = request.form['password']
            if password_attempt == IMPORT_PASSWORD:
                file = request.files['file']
                table_name = request.form['table_name']
                if file.filename.endswith('.xlsx'):
                    file.save('data.xlsx')
                    if import_excel_to_mysql('data.xlsx', table_name):
                        return redirect(url_for('home'))
                    else:
                        return "Failed to import data."
                else:
                    return "Please upload an Excel file (.xlsx)."
            else:
                return "Incorrect password. Please try again."

        return render_template('import.html')
    return render_template('login.html')

# Route to search page
# @app.route('/search', methods=['GET', 'POST'])
# def search():
#     if request.method == 'POST':
#         query = request.form['id']
#         firstname = request.form['firstname']
#         lastname = request.form['lastname']
#         dob = request.form['dob']
#         results = search_in_mysql(query, firstname, lastname, dob)
#         return render_template('search.html', results=results)

#     return render_template('search.html', results=None)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'username' not in session:
        flash('You need to login first', 'warning')
        return redirect(url_for('login'))

    if 'search_count' not in session:
        session['search_count'] = 0
        session['last_search_time'] = datetime.now(timezone.utc)

    user_id = session.get('id')

    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
            user = cursor.fetchone()

            if user:
                current_credit = user['credit']
            else:
                current_credit = None  # Handle case where user is not found

            if request.method == 'POST':
                # Check time limit for search
                last_search_time_utc = session['last_search_time']
                if datetime.now(timezone.utc) - last_search_time_utc > timedelta(minutes=30):
                    session['search_count'] = 0  # Reset search count if time limit exceeded
                    session['last_search_time'] = datetime.now(timezone.utc)

                if session['search_count'] >= 20:
                    flash('You have exceeded the search limit (60 records in 30 minutes). Please try again later.', 'warning')
                    return redirect(url_for('home'))

                # Increment search count
                session['search_count'] += 1

                # Decrement user's credit by 1 if it's greater than 0
                if current_credit is not None and current_credit > 0:
                    new_credit = current_credit - 1
                    cursor.execute(f"UPDATE users SET credit = {new_credit} WHERE id = '{user_id}'")
                    connection.commit()
                    print(f"User {user_id}: Credit decremented from {current_credit} to {new_credit}")

                    # Check if credit becomes zero or less
                    if new_credit <= 0:
                        return render_template('credit_zero.html', user=user)

                else:
                    # Handle case where current_credit is None or <= 0
                    return render_template('credit_zero.html', user=user)

            # Perform search based on form data (not implemented in this snippet)
            query = request.form.get('id')
            firstname = request.form.get('firstname')
            lastname = request.form.get('lastname')
            dob = request.form.get('dob')
            type_ = request.form.get('type')
            results = search_in_mysql(query, firstname, lastname, dob, type_)

            return render_template('search.html', results=results, current_credit=current_credit)

    except Error as e:
        print(f"Error accessing database: {e}")
        flash(f"Error accessing database: {e}", 'danger')

    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

    return render_template('search.html', results=None, current_credit=current_credit)

@app.route('/users')
def users():
    if 'role' in session and session['role'] == 'admin':
        try:
            connection = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
            
            if connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                sql = "SELECT * FROM users"
                cursor.execute(sql)
                users = cursor.fetchall()
                return render_template('users.html', users=users)
            else:
                flash('Error connecting to database', 'danger')
        except Error as e:
            flash(f"Error: {e}", 'danger')
        finally:
            if 'connection' in locals():
                connection.close()
        
        return render_template('users.html', users=None)
    return render_template('login.html')

def get_users():
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            return users
        else:
            flash('Error connecting to database', 'danger')
            return []
    except Error as e:
        flash(f"Error: {e}", 'danger')
        return []
    finally:
        if 'connection' in locals():
            connection.close()

# Route to display users index page
@app.route('/index_users')
def index_users():
    if 'role' in session and session['role'] == 'admin':
        users = get_users()
        return render_template('users_index.html', users=users)
    else:
        return render_template('login.html')
    

def get_user_by_id(user_id):
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            return user
        else:
            return None
    except Error as e:
        print(f"Error: {e}")
        return None
    finally:
        if 'connection' in locals():
            connection.close()

# Route to update user credit
@app.route('/users_credit', methods=['POST'])
def update_user_credit():
    data = request.json
    userId = int(data['userId'])
    creditChange = int(data['creditChange'])

    # Fetch user from database
    user = get_user_by_id(userId)

    if user:
        # Update user credit
        current_credit = user.get("credit", 0)  # Get current credit or default to 0
        if(current_credit == None):
            current_credit = 0
        new_credit = int(current_credit) + creditChange

        try:
            connection = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )

            if connection.is_connected():
                cursor = connection.cursor()
                sql = "UPDATE users SET credit = %s WHERE id = %s"
                cursor.execute(sql, (new_credit, userId))
                connection.commit()
                user["credit"] = new_credit  # Update local user object

                return jsonify({'message': 'Credit updated successfully', 'user': user}), 200
            else:
                return jsonify({'error': 'Error connecting to database'}), 500
        except Error as e:
            print(f"Error: {e}")
            return jsonify({'error': 'Database error occurred'}), 500
        finally:
            if 'connection' in locals():
                connection.close()
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'role' in session and session['role'] == 'admin':
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']
            status = request.form.get('status', 0)  # Assuming status is a checkbox
            
            try:
                connection = mysql.connector.connect(
                    host=MYSQL_HOST,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    database=MYSQL_DB
                )
                
                if connection.is_connected():
                    cursor = connection.cursor()
                    sql = "INSERT INTO users (username, password, role, status) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql, (username, password, role, status))
                    connection.commit()
                    flash('User added successfully', 'success')
                    return redirect(url_for('users'))
                else:
                    flash('Error connecting to database', 'danger')
            except Error as e:
                flash(f"Error: {e}", 'danger')
            finally:
                if 'connection' in locals():
                    connection.close()
        
        return render_template('add_user.html')
    return render_template('login.html')

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'role' in session and session['role'] == 'admin':
        try:
            connection = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
            
            if connection.is_connected():
                cursor = connection.cursor()
                sql = "DELETE FROM users WHERE id = %s"
                cursor.execute(sql, (user_id,))
                connection.commit()
                flash('User deleted successfully', 'success')
            else:
                flash('Error connecting to database', 'danger')
        except Error as e:
            flash(f"Error: {e}", 'danger')
        finally:
            if 'connection' in locals():
                connection.close()
        
        return redirect(url_for('users'))
    return render_template('login.html')

@app.route('/toggle_status/<int:user_id>/<int:new_status>', methods=['POST'])
def toggle_status(user_id, new_status):
    try:
        connection = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # Update user status in the database
            update_sql = "UPDATE users SET status = %s WHERE id = %s"
            cursor.execute(update_sql, (new_status, user_id))
            connection.commit()

            # Return updated status
            return jsonify({'response': 'ok'})

    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return jsonify({'error': 'Database error'})

    finally:
        if 'connection' in locals():
            connection.close()

    return jsonify({'error': 'Unknown error'})


# @app.route('/search', methods=['GET', 'POST'])
# def search():
#     if request.method == 'POST':
#         if 'search_count' not in session:
#             session['search_count'] = 0
#             session['last_search_time'] = datetime.now()

#         if datetime.now() - session['last_search_time'] > timedelta(minutes=30):
#             session['search_count'] = 0  
#             flash('You have exceeded the search limit. Please try again later.', 'warning')
#             return redirect(url_for('home'))

#         session['search_count'] += 1
#         session['last_search_time'] = datetime.now()

#         if session['search_count'] > 60:
#             flash('You have reached the maximum search limit (60 records) within 30 minutes.', 'warning')
#             return redirect(url_for('home'))

#         query = request.form['id']
#         firstname = request.form['firstname']
#         lastname = request.form['lastname']
#         dob = request.form['dob']
#         results = search_in_mysql(query, firstname, lastname, dob)
#         return render_template('search.html', results=results)

#     return render_template('search.html', results=None)
# @app.route('/search', methods=['GET', 'POST'])
# def search():
#     if 'username' not in session:
#         flash('You need to login first', 'warning')
#         return redirect(url_for('login'))

#     if 'search_count' not in session:
#         session['search_count'] = 0
#         session['last_search_time'] = datetime.now(timezone.utc)

#     # Convert session['last_search_time'] to UTC naive datetime
#     last_search_time_utc_naive = session['last_search_time'].astimezone(timezone.utc).replace(tzinfo=None)

#     # Check if 30 minutes have passed since the last search
#     if datetime.now(timezone.utc) - last_search_time_utc_naive > timedelta(minutes=30):
#         session['search_count'] = 0  # Reset search count if time limit exceeded
#         flash('You have exceeded the search limit. Please try again later.', 'warning')
#         return redirect(url_for('home'))

#     # Increment search count
#     session['search_count'] += 1
#     session['last_search_time'] = datetime.now(timezone.utc)

#     # Check if search count exceeds limit (60 records)
#     if session['search_count'] > 60:
#         flash('You have reached the maximum search limit (60 records) within 30 minutes.', 'warning')
#         return redirect(url_for('home'))

#     # Proceed with database search
#     query = request.form['id']
#     firstname = request.form['firstname']
#     lastname = request.form['lastname']
#     dob = request.form['dob']
#     results = search_in_mysql(query, firstname, lastname, dob)
#     return render_template('search.html', results=results)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)  # Example for HTTP
