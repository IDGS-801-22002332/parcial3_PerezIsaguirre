from flask import Flask, render_template, request, redirect, flash, session, url_for
import forms
import os
from flask_wtf.csrf import CSRFProtect
from models import db, Pedido, Usuarios
from config import DevelopmentConfig
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash

app = Flask(__name__)


app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)
csr = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  
login_manager.login_message = "Por favor, inicie sesión para acceder a esta página."


@login_manager.user_loader
def load_user(user_id):
    return Usuarios.query.get(int(user_id))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:  
        return redirect(url_for("pizza"))

    classuser = forms.UsuarioFrom(request.form)

    if request.method == "POST":
        usuario = request.form["usuario"]
        contrasenia = request.form["contrasenia"]

        user = Usuarios.query.filter_by(usuario=usuario).first()

        if user and user.contrasenia == contrasenia:
            login_user(user)
            session["user_id"] = user.id
            return redirect(url_for("pizza"))
        else:
            flash("Usuario o contraseña incorrectos", "danger")
            return redirect(url_for("login"))

    return render_template("index.html", form=classuser)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    classuser = forms.UsuarioFrom(request.form)
    if request.method == 'POST':
        nombre = request.form.get('floating_first_name')
        apellido = request.form.get('floating_last_name')
        telefono = request.form.get('floating_phone')
        correo = request.form.get('floating_email')
        usuario = request.form.get('floating_usuario')  
        contrasenia = request.form.get('floating_password')

        if Usuarios.query.filter_by(usuario=usuario).first():
            flash('El nombre de usuario ya existe. Intenta con otro.', 'danger')
            return redirect(url_for('registro'))

        if Usuarios.query.filter_by(correo=correo).first():
            flash('El correo ya está registrado.', 'danger')
            return redirect(url_for('registro'))

        nuevo_usuario = Usuarios(
            nombre=nombre,
            apellido=apellido,
            telefono=telefono,
            correo=correo,
            usuario=usuario,
            contrasenia=contrasenia
        )

        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash('Cuenta creada con éxito. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error: {str(e)}', 'danger')

    return render_template('cuenta.html',form=classuser)


@app.route("/logout")
@login_required
def logout():
    logout_user()  
    session.clear()  
    return redirect(url_for("login"))


PEDIDOS_FILE = "pedidos.txt"

def leer_pedidos():
    pedidos = []
    cliente = {"nombre": "", "direccion": "", "telefono": ""}

    if os.path.exists(PEDIDOS_FILE):
        with open(PEDIDOS_FILE, "r") as file:
            lineas = file.readlines()
            if lineas:
                datos_cliente = lineas[0].strip().split("|")
                if len(datos_cliente) == 3:
                    cliente = {"nombre": datos_cliente[0], "direccion": datos_cliente[1], "telefono": datos_cliente[2]}
                for linea in lineas[1:]:
                    datos_pedido = linea.strip().split("|")
                    if len(datos_pedido) == 5:
                        pedidos.append({
                            "tamanio": datos_pedido[0],
                            "ingredientes": datos_pedido[1],
                            "num_pizzas": datos_pedido[2],
                            "precio_unitario": datos_pedido[3],
                            "subtotal": datos_pedido[4]
                        })
    
    return cliente, pedidos

def guardar_pedido(cliente, pedido):
    with open(PEDIDOS_FILE, "a") as file:
        if os.stat(PEDIDOS_FILE).st_size == 0:  
            file.write(f"{cliente['nombre']}|{cliente['direccion']}|{cliente['telefono']}\n")
        file.write(f"{pedido['tamanio']}|{pedido['ingredientes']}|{pedido['num_pizzas']}|{pedido['precio_unitario']}|{pedido['subtotal']}\n")

def borrar_pedidos():
    if os.path.exists(PEDIDOS_FILE):
        with open(PEDIDOS_FILE, "w") as file:
            file.write("") 

def borrar_ultimo_pedido():
    if os.path.exists(PEDIDOS_FILE):
        with open(PEDIDOS_FILE, "r") as file:
            lineas = file.readlines()

        if len(lineas) > 1: 
            with open(PEDIDOS_FILE, "w") as file:
                file.write(lineas[0]) 
                file.writelines(lineas[1:-1])  

    cliente, _ = leer_pedidos()
    return cliente  

@app.route("/pizzas", methods=["GET", "POST"])
@login_required
def pizza():
    if "user_id" not in session:
        flash("Ingrese su usuario y contraseña para poder ingresar", "warning")
        return redirect(url_for("login"))
    
    pizza_class = forms.PizzaForm(request.form)
    cliente, pedidos = leer_pedidos()

    precios_pizza = {"Chica": 40, "Mediana": 80, "Grande": 120}
    precios_ingredientes = {"jamon": 10, "piña": 10, "champiñones": 10}

    cliente_reciente = db.session.query(Pedido).order_by(Pedido.id.desc()).first()
    subtotal_total = db.session.query(db.func.sum(Pedido.subtotal)).scalar() or 0

    pedidos_filtrados = []
    subtotal_filtrado = 0

    if request.method == "POST":
        if "btnBuscarFecha" in request.form:
            dia_busqueda = request.form.get("dia_busqueda")
            mes_busqueda = request.form.get("mes_busqueda")

            if dia_busqueda and mes_busqueda:
                pedidos_filtrados = (
                    db.session.query(Pedido)
                    .filter(Pedido.dia == dia_busqueda, Pedido.mes == mes_busqueda)
                    .all()
                )

                subtotal_filtrado = sum(p.subtotal for p in pedidos_filtrados)

        elif pizza_class.validate():
            nombre = pizza_class.nombre.data
            direccion = pizza_class.direccion.data
            telefono = pizza_class.telefono.data
            dia = pizza_class.dia.data
            mes = pizza_class.mes.data
            anio = pizza_class.anio.data
            cliente = {"nombre": nombre, "direccion": direccion, "telefono": telefono, "dia": dia, "mes": mes, "anio": anio}

            if "btnAgregar" in request.form:
                tamanio = pizza_class.tamanio.data
                ingredientes = pizza_class.ingredientes.data
                num_pizzas = int(pizza_class.numPizzas.data)

                precio_pizza = precios_pizza.get(tamanio, 0)
                precio_ingredientes_total = sum(precios_ingredientes.get(ing, 0) for ing in ingredientes)
                precio_unitario = precio_pizza + precio_ingredientes_total
                subtotal = precio_unitario * num_pizzas

                pedido = {
                    "tamanio": tamanio,
                    "ingredientes": ", ".join(ingredientes),
                    "num_pizzas": str(num_pizzas),
                    "precio_unitario": f"${precio_unitario}",
                    "subtotal": f"${subtotal}"
                }

                guardar_pedido(cliente, pedido)
                pedidos.append(pedido)

            elif "btnQuitar" in request.form:
                borrar_ultimo_pedido()
                cliente, pedidos = leer_pedidos()

            elif "btnTerminar" in request.form:
                total = sum(float(p["subtotal"].replace("$", "")) for p in pedidos)

                for p in pedidos:
                    nuevo_pedido = Pedido(
                        nombre=cliente["nombre"],
                        direccion=cliente["direccion"],
                        telefono=cliente["telefono"],
                        dia=cliente["dia"],
                        mes=cliente["mes"],
                        anio=cliente["anio"],
                        tamanio=p["tamanio"],
                        ingredientes=p["ingredientes"],
                        num_pizzas=int(p["num_pizzas"]),
                        precio_unitario=float(p["precio_unitario"].replace("$", "")),
                        subtotal=float(p["subtotal"].replace("$", ""))
                    )
                    db.session.add(nuevo_pedido)

                db.session.commit()

                flash(f"Su pedido fue realizado. Su total es de: ${total}", "success")
                borrar_pedidos()
                return redirect("/")

    return render_template("pizzas.html",form=pizza_class,nom=cliente["nombre"],dir=cliente["direccion"],tel=cliente["telefono"],cliente_reciente=cliente_reciente,subtotal_total=subtotal_total,pedidos=pedidos,pedidos_filtrados=pedidos_filtrados,subtotal_filtrado=subtotal_filtrado,
    )
    
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    csr.init_app(app)
    app.run(debug=True, port=3000)
