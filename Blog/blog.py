from flask import Flask, render_template, flash, redirect, url_for, session, logging, request, Response
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

# Kullanıcı Giriş Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Bu Sayfayı Görüntülemek İçin Lütfen Giriş Yapın. ', 'danger')
            return redirect(url_for('login'))
    return decorated_function

# Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField('İsim Soyisim', validators = [validators.length(min = 5, max = 99, message = 'En az 5 Karakter ve en fazla 99 karakter kullanabilirsin.')])
    username = StringField('Kullanıcı Adı', validators = [validators.length(min = 5, max = 25, message = 'En az 5 Karakter ve en fazla 25 karakter kullanabilirsin')])
    email = StringField('Email', validators = [validators.Email(message = 'Lütfen Geçerli bir email adresi giriniz.')])
    password = PasswordField('Parola: ', validators = [validators.DataRequired(message = 'Lütfen bir parola belirleyiniz.'),
    validators.equal_to(fieldname = 'confirm', message = 'Parola birbiriyle uyuşmamaktadır.')
    ])
    confirm = PasswordField('Parola Doğrula')

# Login Form
class LoginForm(Form):
    username = StringField('Kullanıcı Adı')
    password = PasswordField('Parola')

app = Flask(__name__)
app.secret_key = 'blog'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'blog'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

# Makale Sayfası

@app.route('/articles')
@login_required
def articles():
    cursor = mysql.connection.cursor()
    sorgu = 'Select * From articles'
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template('articles.html', articles = articles)
    else:
        return render_template('articles.html')

@app.route('/dashboard')
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = 'Select * From articles where author = %s'
    result = cursor.execute(sorgu,(session['username'],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template('dashboard.html', articles = articles)
    else:
        return render_template('dashboard.html')

# Kayıt olma
@app.route('/register',methods = ['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    
    if request.method == 'POST' and form.validate():
        
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        cursor = mysql.connection.cursor()
        sorgu = 'Insert into users(name, email, username, password) VALUES(%s, %s, %s, %s)'
        cursor.execute(sorgu,(name, email, username, password))
        mysql.connection.commit()
        cursor.close()
        flash('Kayıt Başarılı Şekilde oluşturuldu.', category='success')
        return redirect(url_for('login'))
    
    else:
        return render_template('register.html', form = form)

# Login İşlemi 
@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST':
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()
        sorgu = 'Select * From users where username = %s'
        result = cursor.execute(sorgu,(username,))

        if result > 0:
            data = cursor.fetchone()
            real_pass = data['password']
            if sha256_crypt.verify(password_entered, real_pass):
                flash('Giriş Başarılı', 'success')
                
                session['logged_in'] = True
                session['username'] = username

                return redirect(url_for('index'))
            else:
                flash('Parola yanlış lütfen tekrar deneyiniz. ', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Böyle bir kullanıcı bulunmuyor.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', form = form)
# Detay Sayfası
@app.route('/article/<string:id>')
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = 'Select * From articles where id = %s'
    result = cursor.execute(sorgu,(id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template('article.html', article = article) 
    else:
        return render_template('article.html')
    
# Logout İşlemi
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Makale Ekle
@app.route('/addarticle', methods=['GET', 'POST'])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        tittle = form.tittle.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = 'Insert into articles(tittle, author, content) VALUES(%s, %s, %s)'
        cursor.execute(sorgu,(tittle,session['username'], content))
        mysql.connection.commit()
        cursor.close()

        flash('Makale Başarıyla Eklendi...', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('addarticle.html', form = form)
# Makale Silme
@app.route('/delete/<string:id>')
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = 'Select * From articles where author = %s and id = %s'
    result = cursor.execute(sorgu,(session['username'],id))

    if result > 0:
        new_sorgu = 'Delete from articles where id = %s'
        cursor.execute(new_sorgu,(id,))
        mysql.connection.commit()
        return redirect(url_for('dashboard'))
    else:
        flash('Böyle bir makale yok veya Bu işleme yetkiniz yok', 'danger')
        return redirect(url_for('index'))
# Makale Güncelle 
@app.route('/edit/<string:id>', methods = ['GET', 'POST'])
@login_required
def update(id):
    if request.method == 'GET':
        cursor = mysql.connection.cursor()
        sorgu = 'Select * From articles where id = %s and author = %s'
        result = cursor.execute(sorgu,(id,session['username']))

        if result == 0:
            flash('Böyle bir makale yok veya Bu işleme yetkiniz yok', 'danger')
            return redirect(url_for('index'))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.tittle.data = article['tittle']
            form.content.data = article ['content']

            return render_template('update.html', form = form)
    else:
        form = ArticleForm(request.form)
        new_tittle = form.tittle.data
        new_content = form.content.data

        new_sorgu = 'Update articles Set tittle = %s, content = %s where id = %s'
        cursor = mysql.connection.cursor()
        cursor.execute(new_sorgu,(new_tittle, new_content, id))
        mysql.connection.commit()

        flash('Makale Başarıyla Güncellendi.', 'success')
        return redirect((url_for('dashboard')))
        
# Arama URL
@app.route('/search', methods = ['GET', 'POST'])
def search():
    if request.method == 'GET':
        return redirect(url_for('index'))
    else:
        keyword = request.form.get('keyword')
        cursor = mysql.connection.cursor()
        sorgu = 'Select * From articles where tittle like %s'
        result = cursor.execute(sorgu,('%' + keyword + '%',))

        if result == 0:
            flash('Böyle bir makale bulunamadı.', 'warning')
            return redirect(url_for('articles'))
        else:
            articles = cursor.fetchall()
            return render_template('articles.html', articles = articles )
# Makale Formu
class ArticleForm(Form):
    tittle = StringField('Makale Başlığı', validators=[validators.length(min = 5, max = 100)])
    content = TextAreaField('Makale İçeriği', validators=[validators.length(min = 10)])

if __name__ == '__main__':
    app.run(debug = True)