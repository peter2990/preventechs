from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

# Configuración de la aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mantenimiento.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelos de base de datos
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo_electronico = db.Column(db.String(120), unique=True, nullable=False)
    contrasena = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(10), nullable=False)  # gerente o tecnico

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    area = db.Column(db.String(100), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(255), nullable=False)
    fecha_asignacion = db.Column(db.DateTime, default=db.func.current_timestamp())
    fecha_inicio = db.Column(db.DateTime)
    fecha_finalizacion = db.Column(db.DateTime)
    estado = db.Column(db.String(20), default='pendiente')

    equipo_id = db.Column(db.Integer, db.ForeignKey('equipment.id'))
    tecnico_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    equipo = db.relationship('Equipment', backref='orders')
    tecnico = db.relationship('User', backref='orders')

# Funciones de carga de usuario
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Generar PDF de productividad
def generate_pdf(tecnico, ordenes_completadas, tiempo_total):
    filename = 'productivity_report.pdf'
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(100, 750, f'Reporte de Productividad')
    c.drawString(100, 730, f'Técnico: {tecnico}')
    c.drawString(100, 710, f'Órdenes Completadas: {ordenes_completadas}')
    c.drawString(100, 690, f'Tiempo Total: {tiempo_total} horas')
    c.save()
    return filename

# Rutas de la aplicación
@app.route('/')
@login_required
def index():
    return render_template('orders.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo_electronico = request.form['correo_electronico']
        contrasena = request.form['contrasena']
        user = User.query.filter_by(correo_electronico=correo_electronico).first()
        if user and check_password_hash(user.contrasena, contrasena):
            login_user(user)
            return redirect(url_for('index'))
        flash('Correo electrónico o contraseña incorrectos.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/orders')
@login_required
def orders():
    orders = Order.query.all()
    return render_template('orders.html', orders=orders)

@app.route('/create-order', methods=['GET', 'POST'])
@login_required
def create_order():
    if request.method == 'POST':
        descripcion = request.form['descripcion']
        equipo_id = request.form['equipo_id']
        tecnico_id = request.form['tecnico_id']
        new_order = Order(descripcion=descripcion, equipo_id=equipo_id, tecnico_id=tecnico_id)
        db.session.add(new_order)
        db.session.commit()
        return redirect(url_for('orders'))
    equipos = Equipment.query.all()
    tecnicos = User.query.filter_by(rol='tecnico').all()
    return render_template('create_order.html', equipos=equipos, tecnicos=tecnicos)

@app.route('/generate-report', methods=['POST'])
@login_required
def generate_report():
    tecnico = request.form['tecnico']
    ordenes_completadas = int(request.form['ordenes_completadas'])
    tiempo_total = float(request.form['tiempo_total'])
    pdf_file = generate_pdf(tecnico, ordenes_completadas, tiempo_total)
    return send_file(pdf_file, as_attachment=True)

# HTML embebido en Flask
@app.route('/templates/<path>')
def serve_static(path):
    return send_file(os.path.join('templates', path))

# HTML para login
@app.route('/login.html')
def login_html():
    return '''
    {% extends "base.html" %}
    {% block content %}
    <div class="row justify-content-center">
        <div class="col-md-4">
            <h3 class="text-center">Iniciar Sesión</h3>
            <form method="POST" action="{{ url_for('login') }}">
                <div class="form-group">
                    <label for="correo_electronico">Correo Electrónico</label>
                    <input type="email" class="form-control" id="correo_electronico" name="correo_electronico" required>
                </div>
                <div class="form-group">
                    <label for="contrasena">Contraseña</label>
                    <input type="password" class="form-control" id="contrasena" name="contrasena" required>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Iniciar Sesión</button>
            </form>
        </div>
    </div>
    {% endblock %}
    '''

# HTML para ordenes
@app.route('/orders.html')
def orders_html():
    return '''
    {% extends "base.html" %}
    {% block content %}
    <h3 class="text-center">Órdenes de Trabajo</h3>
    <table class="table table-hover">
        <thead class="thead-dark">
            <tr>
                <th scope="col">Descripción</th>
                <th scope="col">Equipo</th>
                <th scope="col">Técnico</th>
                <th scope="col">Estado</th>
                <th scope="col">Fecha Asignación</th>
                <th scope="col">Fecha Inicio</th>
                <th scope="col">Fecha Finalización</th>
            </tr>
        </thead>
        <tbody>
            {% for order in orders %}
            <tr>
                <td>{{ order.descripcion }}</td>
                <td>{{ order.equipo.nombre }}</td>
                <td>{{ order.tecnico.nombre }}</td>
                <td>{{ order.estado }}</td>
                <td>{{ order.fecha_asignacion }}</td>
                <td>{{ order.fecha_inicio or 'No iniciado' }}</td>
                <td>{{ order.fecha_finalizacion or 'No finalizado' }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <a href="{{ url_for('create_order') }}" class="btn btn-success">Crear Nueva Orden</a>
    {% endblock %}
    '''

# HTML para crear orden
@app.route('/create_order.html')
def create_order_html():
    return '''
    {% extends "base.html" %}
    {% block content %}
    <h3 class="text-center">Crear Nueva Orden</h3>
    <form method="POST" action="{{ url_for('create_order') }}">
        <div class="form-group">
            <label for="descripcion">Descripción</label>
            <input type="text" class="form-control" id="descripcion" name="descripcion" required>
        </div>
        <div class="form-group">
            <label for="equipo_id">Equipo</label>
            <select class="form-control" id="equipo_id" name="equipo_id">
                {% for equipo in equipos %}
                <option value="{{ equipo.id }}">{{ equipo.nombre }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="form-group">
            <label for="tecnico_id">Técnico</label>
            <select class="form-control" id="tecnico_id" name="tecnico_id">
                {% for tecnico in tecnicos %}
                <option value="{{ tecnico.id }}">{{ tecnico.nombre }}</option>
                {% endfor %}
            </select>
        </div>
        <button type="submit" class="btn btn-primary">Crear Orden</button>
    </form>
    {% endblock %}
    '''

# Iniciar la aplicación
if __name__ == '__main__':
    db.create_all()  # Crear tablas si no existen
    app.run(debug=True)
