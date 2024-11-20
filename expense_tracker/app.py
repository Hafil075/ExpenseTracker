from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DecimalField, SelectField, DateField
from wtforms.validators import InputRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expense_tracker.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)


class Category(db.Model):
    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_name = db.Column(db.String(100), nullable=False)
    transactions = db.relationship('Transaction', backref='category', lazy=True)

class Transaction(db.Model):
    transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.category_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    date = db.Column(db.Date, nullable=False)


with app.app_context():
    db.create_all()
    if not Category.query.first():
        db.session.add_all([
            Category(category_name='Food'),
            Category(category_name='Transport'),
            Category(category_name='Utilities'),
            Category(category_name='Entertainment')
        ])
        db.session.commit()


@app.route('/')
def home():
    return render_template('home.html')


# User registration route

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            return "Username already exists. Please choose a different username."
        if User.query.filter_by(email=email).first():
            return "Email already registered. Please use a different email."

        if not username or not email or not password:
            return "All fields are required!"
        
        hashed_password = generate_password_hash(password)
        
        try:
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            return f"An error occurred: {e}"
        
        return redirect(url_for('login'))
    return render_template('register.html')


# User login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.user_id
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    transactions = Transaction.query.filter_by(user_id=user_id).all()
    total_amount = sum(transaction.amount for transaction in transactions)
    categories = db.session.query(Category.category_name, db.func.sum(Transaction.amount)).join(Transaction).filter(Transaction.user_id == user_id).group_by(Category.category_name).all()

    return render_template('dashboard.html', transactions=transactions, total_amount=total_amount, categories=categories)


@app.route('/logout')
def logout():
    # Your existing code to handle logout
    session.clear()
    return redirect(url_for('home'))


@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        amount = request.form.get('amount')
        category_name = request.form.get('category')
        description = request.form.get('description')
        date_str = request.form.get('date')  # Get the date string from the form
        user_id = session.get('user_id')

        category = Category.query.filter_by(category_name=category_name).first()
        if not category:
            return "Category not found!", 404

        try:
            # Convert the date string to a Python date object
            date = datetime.strptime(date_str, '%Y-%m-%d').date()

            new_transaction = Transaction(
                amount=amount,
                category_id=category.category_id,
                description=description,
                date=date,  # Use the date object here
                user_id=user_id
            )
            db.session.add(new_transaction)
            db.session.commit()
            return redirect(url_for('dashboard'))
        except AttributeError as e:
            return f"An error occurred: {e}"
    else:
        categories = Category.query.all()
        return render_template('add_transaction.html', categories=categories)




@app.route('/view_transactions')
def view_transactions():
    user_id = session.get('user_id')
    transactions = Transaction.query.filter_by(user_id=user_id).all()
    return render_template('view_transactions.html', transactions=transactions)


@app.route('/edit_transaction/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return "Transaction not found!", 404
    
    if request.method == 'POST':
        transaction.amount = request.form.get('amount')
        category_name = request.form.get('category')
        transaction.description = request.form.get('description')
        date_str = request.form.get('date')
        transaction.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        category = Category.query.filter_by(category_name=category_name).first()
        if category:
            transaction.category_id = category.category_id

        db.session.commit()
        return redirect(url_for('dashboard'))
    else:
        categories = Category.query.all()
        return render_template('edit_transaction.html', transaction=transaction, categories=categories)


@app.route('/delete_transaction/<int:transaction_id>', methods=['GET', 'POST'])
def delete_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return "Transaction not found!", 404

    db.session.delete(transaction)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/confirm_delete_account')
def confirm_delete_account():
    return render_template('confirm_delete_account.html')

@app.route('/delete_account', methods=['POST'])
def delete_account():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        # Delete associated transactions
        transactions = Transaction.query.filter_by(user_id=user_id).all()
        for transaction in transactions:
            db.session.delete(transaction)
        
        # Delete user account
        db.session.delete(user)
        db.session.commit()
        session.clear()  # Clear session after account deletion
    return redirect(url_for('register'))


if __name__ == '__main__':
    app.run(debug=True)
