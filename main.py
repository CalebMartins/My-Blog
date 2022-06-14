from flask import Flask, render_template, redirect, url_for, flash
from flask_ckeditor import CKEditor
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import *
from flask_gravatar import Gravatar
from functools import wraps
from flask import abort
import os

app = Flask(__name__)

# Create Only Admin Decorator
def admin_only(f):
    @wraps(f)
    # helps prevent decorators from masking identity of the decorated functions. Thus, the functions can keep their metadata(fuction name, docstrings etc.) even after they are decorated by decorators.
    
    def decorated_function(*args, **kwargs):
        
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1 or not current_user.is_authenticated:
            return abort(403)
        
        #Otherwise continue with the route function
        return f(*args, **kwargs)        
    
    return decorated_function

# Connect to Flask Gravator
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

# Flask WTF
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

# Connect to ckeditor
ckeditor = CKEditor(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#connect to login manager
login_manager = LoginManager()
login_manager.init_app(app)


# CONFIGURE TABLES
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    
    #This will act like a List of BlogPost objects attached to each User. 
    #The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates=("comment_author"))

    

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    
    #Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    
    #Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")
   
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    #Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    
    parent_post = relationship("BlogPost", back_populates="comments")
    comment_author = relationship("User", back_populates="comments")
    text = db.Column(db.String(1000))

db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route('/')
def get_all_posts():
    posts = db.session.query(BlogPost).all()
    return render_template("index.html", all_posts=posts)


@app.route("/post/<int:index>", methods=['GET', 'POST'])
def show_post(index):
    form = UserComment()
    requested_post = db.session.query(BlogPost).get(index)
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                parent_post = requested_post,
                comment_author = current_user,
                text = form.comment.data
            )
            db.session.add(new_comment)
            db.session.commit()

        else:
            flash("You need to login to comment!!!")
            return redirect(url_for("login"))
    
    return render_template("post.html", post=requested_post, form=form)


@app.route('/new-post', methods=['GET', 'POST'])
@admin_only
def new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        x = datetime.datetime.now()
        f = f"{x.strftime('%B')} {x.strftime('%d')},{x.strftime('%Y')}"
        new_post = BlogPost(
            title = form.title.data,
            subtitle = form.subtitle.data,
            date = f,
            body = form.body.data,
            author = current_user,
            img_url = form.img_url.data
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('get_all_posts'))
    
    return render_template('make-post1.html', form=form)


@app.route('/edit-post/<int:post_id>', methods=['GET', 'POST'])
@admin_only
def edit_post(post_id):
    post_to_edit = db.session.query(BlogPost).get(post_id)
    
    #Auto fill form fields so the user can edit easily
    edit_form = CreatePostForm(
        title = post_to_edit.title,
        subtitle = post_to_edit.subtitle,
        author = current_user,
        img_url = post_to_edit.img_url,
        body = post_to_edit.body
    )

    if edit_form.validate_on_submit():
        post_to_edit.title = edit_form.title.data
        post_to_edit.subtitle = edit_form.subtitle.data
        post_to_edit.img_url = edit_form.img_url.data
        post_to_edit.body = edit_form.body.data    
        db.session.commit()
        return redirect(url_for('show_post', index=post_to_edit.id))
    
    return render_template('make-post1.html', is_edit=True, form=edit_form, id=post_to_edit.id)


@app.route('/delete-post/<int:post_id>')
@admin_only
def delete_post(post_id):
    post_to_delete = db.session.query(BlogPost).get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/register", methods = ['GET', 'POST'])
def register():
    form = RegisterNewUser()

    if form.validate_on_submit():
        new_user = User(
            email = form.email.data,
            password = generate_password_hash(password=form.password.data, method="pbkdf2:sha256", salt_length=8),
            name = form.name.data
        )
        
        all_users = db.session.query(User).all()
        all_user_emails = [user.email for user in all_users]
        
        if form.email.data not in all_user_emails:
            db.session.add(new_user)
            db.session.commit()
            #Log in and authenticate user after adding details to database.
            login_user(new_user)

            return redirect(url_for('get_all_posts'))
        else:
            flash('This email already exists, login instead!!!.')
            return redirect(url_for('login'))
    
    return render_template("register.html", form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = Login()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        #Find user by email entered.
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash('Password is incorrect')
        else:  
            flash('Email does not exist, please try again.')

    return render_template('login.html', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))

if __name__ == "__main__":
    app.run(debug = True)