# inventario/views.py
from django.db.models import Sum, Count, Max, Min
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse # Para las vistas temporales (dummy)
from django.db import IntegrityError 
from django.db.models import ProtectedError # Para manejar errores de eliminación con llaves foráneas
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import UserPassesTestMixin 
from django.db import transaction # Necesario para transacciones atómicas
from django.db.models import F
from .models import Categoria, Producto, Cliente, Venta, DetalleVenta, MovimientoStock

# =======================================================
# VISTAS DE AUTENTICACIÓN
# =======================================================

def registrar_usuario(request):
    """Registro de nuevos usuarios con validaciones."""
    nick = ''
    nombre_completo = ''
    mensaje = None
    es_error = False

    if request.method == 'POST':
        nick = request.POST.get('nick', '').strip()
        nombre_completo = request.POST.get('nombre_completo', '').strip()
        password = request.POST.get('password', '')

        if not nick or not nombre_completo or not password:
            mensaje = "Error: Todos los campos son obligatorios."
            es_error = True
        elif User.objects.filter(username=nick).exists():
            mensaje = f"Error: El usuario '{nick}' ya está registrado."
            es_error = True
        elif len(password) < 6:
            mensaje = "Error: La contraseña debe tener al menos 6 caracteres."
            es_error = True
        else:
            try:
                partes_nombre = nombre_completo.split(' ', 1)
                first_name = partes_nombre[0] if partes_nombre else nombre_completo
                last_name = partes_nombre[1] if len(partes_nombre) > 1 else ''

                User.objects.create_user(
                    username=nick,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )

                mensaje = f"¡Usuario '{nick}' creado exitosamente!"
                nick = ''
                nombre_completo = ''
            except Exception as e:
                mensaje = f"Error interno: {e}"
                es_error = True

    contexto = {
        'nick_prev': nick,
        'nombre_completo_prev': nombre_completo,
        'mensaje': mensaje,
        'es_error': es_error,
    }

    return render(request, 'registro_usuario.html', contexto)


def login_usuario(request):
    """Login de usuario."""
    nick = ''
    mensaje = None
    es_error = False

    if request.method == 'POST':
        nick = request.POST.get('nick', '').strip()
        password = request.POST.get('password', '')

        if not nick or not password:
            mensaje = "Error: Usuario y contraseña son obligatorios."
            es_error = True
        else:
            user = authenticate(request, username=nick, password=password)
            if user is not None:
                login(request, user)
                return redirect('home_inventario')
            else:
                mensaje = "Error: Credenciales incorrectas."
                es_error = True

    contexto = {'nick_prev': nick, 'mensaje': mensaje, 'es_error': es_error}
    return render(request, 'login_usuario.html', contexto)


def logout_usuario(request):
    """Cerrar sesión y redirigir al login."""
    logout(request)
    return redirect('login_usuario')


# =======================================================
# VISTAS DEL SISTEMA (Requieren Login)
# =======================================================



# -------------------------------------------------------
# CRUD DE CATEGORÍAS
# -------------------------------------------------------

@login_required
def crear_categoria(request):
    """Crear nueva categoría con validaciones."""
    nombre_categoria = ''
    mensaje = None
    es_error = False

    if request.method == 'POST':
        nombre_categoria = request.POST.get('nombre', '').strip()

        if not nombre_categoria:
            mensaje = "Error: El nombre de la categoría es obligatorio."
            es_error = True
        elif Categoria.objects.filter(nombre__iexact=nombre_categoria).exists():
            mensaje = f"Error: La categoría '{nombre_categoria}' ya existe."
            es_error = True
        else:
            try:
                Categoria.objects.create(nombre=nombre_categoria)
                mensaje = f"Categoría '{nombre_categoria}' creada exitosamente."
                nombre_categoria = ''
            except Exception as e:
                mensaje = f"Error al guardar la categoría: {e}"
                es_error = True

    contexto = {'nombre_prev': nombre_categoria, 'mensaje': mensaje, 'es_error': es_error}
    return render(request, 'categoria_form.html', contexto)


@login_required
def listar_categorias(request):
    categorias = Categoria.objects.all().order_by('nombre')
    return render(request, 'categoria_listado.html', {'categorias': categorias})


@login_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    nombre_prev = categoria.nombre
    mensaje = None
    es_error = False

    if request.method == 'POST':
        nombre_nuevo = request.POST.get('nombre', '').strip()

        if not nombre_nuevo:
            mensaje = "Error: El nombre no puede estar vacío."
            es_error = True
        elif Categoria.objects.filter(nombre__iexact=nombre_nuevo).exclude(pk=pk).exists():
            mensaje = f"Error: La categoría '{nombre_nuevo}' ya existe."
            es_error = True
        else:
            try:
                categoria.nombre = nombre_nuevo
                categoria.save()
                return redirect('listar_categorias')
            except Exception:
                mensaje = "Error al actualizar la categoría."
                es_error = True
        nombre_prev = nombre_nuevo

    contexto = {
        'nombre_prev': nombre_prev,
        'mensaje': mensaje,
        'es_error': es_error,
        'categoria_pk': pk,
        'titulo_form': f'Editar Categoría: {categoria.nombre}',
    }
    return render(request, 'categoria_form.html', contexto)


@login_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        try:
            categoria.delete()
        except ProtectedError:
            pass
    return redirect('listar_categorias')


# -------------------------------------------------------
# CRUD DE PRODUCTOS
# -------------------------------------------------------

@login_required
def crear_producto(request):
    """Crear nuevo producto."""
    nombre_producto = ''
    stock_prev = ''
    precio_prev = ''
    categoria_id_prev = ''
    mensaje = None
    es_error = False
    categorias = Categoria.objects.all().order_by('nombre')

    if request.method == 'POST':
        nombre_producto = request.POST.get('nombre', '').strip()
        stock_prev = request.POST.get('stock', '').strip()
        precio_prev = request.POST.get('precio', '').strip()
        categoria_id_prev = request.POST.get('categoria', '').strip()

        if not nombre_producto or not stock_prev or not precio_prev or not categoria_id_prev:
            mensaje = "Error: Todos los campos son obligatorios."
            es_error = True
        else:
            try:
                stock_int = int(stock_prev)
                precio_float = float(precio_prev)
                if Producto.objects.filter(nombre__iexact=nombre_producto).exists():
                    mensaje = f"Error: El producto '{nombre_producto}' ya existe."
                    es_error = True
                else:
                    categoria_obj = Categoria.objects.get(pk=categoria_id_prev)
                    Producto.objects.create(
                        nombre=nombre_producto,
                        stock=stock_int,
                        precio=precio_float,
                        categoria=categoria_obj
                    )
                    mensaje = f"Producto '{nombre_producto}' creado exitosamente."
                    nombre_producto = ''
                    stock_prev = ''
                    precio_prev = ''
                    categoria_id_prev = ''
            except ValueError:
                mensaje = "Error: Stock y Precio deben ser numéricos."
                es_error = True
            except Categoria.DoesNotExist:
                mensaje = "Error: Categoría no válida."
                es_error = True
            except IntegrityError as e:
                mensaje = f"Error de base de datos: {e}"
                es_error = True

    contexto = {
        'nombre_prev': nombre_producto,
        'stock_prev': stock_prev,
        'precio_prev': precio_prev,
        'categoria_id_prev': categoria_id_prev,
        'mensaje': mensaje,
        'es_error': es_error,
        'categorias': categorias,
    }
    return render(request, 'producto_form.html', contexto)


@login_required
def listar_productos(request):
    productos = Producto.objects.select_related('categoria').all().order_by('nombre')
    return render(request, 'producto_listado.html', {'productos': productos})


@login_required
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        return redirect('listar_productos')
    return redirect('listar_productos')


@login_required
def editar_producto(request, pk):
    """Editar un producto existente."""
    producto = get_object_or_404(Producto, pk=pk)
    nombre_producto = producto.nombre
    stock_prev = producto.stock
    precio_prev = producto.precio
    categoria_id_prev = producto.categoria.pk
    mensaje = None
    es_error = False
    categorias = Categoria.objects.all().order_by('nombre')

    if request.method == 'POST':
        nombre_nuevo = request.POST.get('nombre', '').strip()
        stock_prev = request.POST.get('stock', '').strip()
        precio_prev = request.POST.get('precio', '').strip()
        categoria_id_prev = request.POST.get('categoria', '').strip()

        if not nombre_nuevo or not stock_prev or not precio_prev or not categoria_id_prev:
            mensaje = "Error: Todos los campos son obligatorios."
            es_error = True
        else:
            try:
                stock_int = int(stock_prev)
                precio_float = float(precio_prev)
                if Producto.objects.filter(nombre__iexact=nombre_nuevo).exclude(pk=pk).exists():
                    mensaje = f"Error: El nombre '{nombre_nuevo}' ya existe."
                    es_error = True
                else:
                    categoria_obj = Categoria.objects.get(pk=categoria_id_prev)
                    producto.nombre = nombre_nuevo
                    producto.stock = stock_int
                    producto.precio = precio_float
                    producto.categoria = categoria_obj
                    producto.save()
                    return redirect('listar_productos')
            except ValueError:
                mensaje = "Error: Stock y Precio deben ser numéricos."
                es_error = True
            except Categoria.DoesNotExist:
                mensaje = "Error: Categoría no válida."
                es_error = True
            except Exception as e:
                mensaje = f"Error desconocido: {e}"
                es_error = True

    contexto = {
        'nombre_prev': nombre_producto,
        'stock_prev': stock_prev,
        'precio_prev': precio_prev,
        'categoria_id_prev': str(categoria_id_prev),
        'mensaje': mensaje,
        'es_error': es_error,
        'categorias': categorias,
        'producto_pk': pk,
        'titulo_form': f"Editar Producto: {producto.nombre}",
    }
    return render(request, 'producto_form.html', contexto)

@login_required
@user_passes_test(lambda user: user.is_staff)
def listar_usuarios(request):
    """Muestra la tabla con todos los usuarios registrados (excluyendo al propio admin)."""
    
    # Excluye al usuario actual de la lista para prevenir errores de auto-eliminación
    usuarios = User.objects.all().exclude(pk=request.user.pk).order_by('username')
    
    contexto = {
        'usuarios': usuarios,
        'titulo_modulo': 'CRUD de Usuarios',
    }
    return render(request, 'usuario_listado.html', contexto)

@login_required
@user_passes_test(lambda user: user.is_staff)
def crear_usuario(request):
    """Formulario y lógica para crear un nuevo usuario."""
    
    # Valores iniciales para el formulario
    usuario_prev = {'username': '', 'nombre_completo': '', 'is_staff': False}
    mensaje = None
    es_error = False

    if request.method == 'POST':
        # 1. Capturar datos
        username = request.POST.get('username', '').strip()
        nombre_completo = request.POST.get('nombre_completo', '').strip()
        password = request.POST.get('password', '')
        es_staff = request.POST.get('is_staff', 'off') == 'on'
        
        # 2. Asignar valores al contexto de error (para repoblar el formulario)
        usuario_prev = {'username': username, 'nombre_completo': nombre_completo, 'is_staff': es_staff}

        # 3. Validaciones
        if not username or not password or not nombre_completo:
            mensaje = "Error: Todos los campos son obligatorios (Usuario, Nombre y Contraseña)."
            es_error = True
        elif len(password) < 6:
            mensaje = "Error: La contraseña debe tener al menos 6 caracteres."
            es_error = True
        elif User.objects.filter(username=username).exists():
            mensaje = f"Error: El nombre de usuario '{username}' ya está registrado."
            es_error = True
        else:
            try:
                # 4. Crear usuario
                partes_nombre = nombre_completo.split(' ', 1)
                
                User.objects.create(
                    username=username,
                    password=make_password(password), # IMPORTANTE: Cifrar contraseña
                    first_name=partes_nombre[0] if partes_nombre else '',
                    last_name=partes_nombre[1] if len(partes_nombre) > 1 else '',
                    is_staff=es_staff,
                    is_active=True # Activarlo por defecto
                )
                
                # Redirigir al listado después de crear
                return redirect('listar_usuarios') 
                
            except Exception as e:
                mensaje = f"Error interno al guardar el usuario: {e}"
                es_error = True

    contexto = {
        'usuario_prev': usuario_prev,
        'mensaje': mensaje,
        'es_error': es_error,
        'titulo_form': "Crear Nuevo Usuario",
    }
    
    return render(request, 'usuario_form.html', contexto)

@login_required
@user_passes_test(lambda user: user.is_staff)
def editar_usuario(request, pk):
    """Permite a un usuario administrador editar la información de otro usuario."""
    
    usuario = get_object_or_404(User, pk=pk)
    
    # Valores iniciales
    nombre_completo_prev = f"{usuario.first_name} {usuario.last_name}".strip()
    es_staff_prev = usuario.is_staff
    
    mensaje = None
    es_error = False

    if request.method == 'POST':
        # 1. Obtener y limpiar datos del POST
        nombre_completo_nuevo = request.POST.get('nombre_completo', '').strip()
        password_nuevo = request.POST.get('password', '')
        es_staff_nuevo = request.POST.get('is_staff', 'off') == 'on' 
        
        # VALIDACIONES
        if not nombre_completo_nuevo:
            mensaje = "Error: El nombre completo del usuario es obligatorio."
            es_error = True
        
        elif password_nuevo and len(password_nuevo) < 6:
            mensaje = "Error: Si proporciona una nueva contraseña, debe tener al menos 6 caracteres."
            es_error = True
            
        else:
            try:
                # 2. Actualizar campos
                
                # Dividir nombre completo en first_name y last_name
                partes_nombre = nombre_completo_nuevo.split(' ', 1)
                usuario.first_name = partes_nombre[0] if partes_nombre else ''
                usuario.last_name = partes_nombre[1] if len(partes_nombre) > 1 else ''
                
                # Actualizar Permiso de Staff (Administrador)
                # Impedir que un admin se auto-desactive
                if usuario.pk != request.user.pk:
                    usuario.is_staff = es_staff_nuevo
                
                # Cambiar Contraseña si se proporciona una nueva
                if password_nuevo:
                    usuario.password = make_password(password_nuevo)
                
                usuario.save()
                
                # Redirigir al listado después de guardar
                return redirect('listar_usuarios') 
                
            except Exception as e:
                mensaje = f"Error interno al actualizar el usuario: {e}"
                es_error = True
                
        # Si hubo un error en POST, actualizamos los valores 'prev' para que se muestren
        nombre_completo_prev = nombre_completo_nuevo
        es_staff_prev = es_staff_nuevo

    contexto = {
        'usuario': usuario,
        'nombre_completo_prev': nombre_completo_prev,
        'es_staff_prev': es_staff_prev,
        'mensaje': mensaje,
        'es_error': es_error,
        'titulo_form': f"Editar Usuario: {usuario.username}",
    }
    
    return render(request, 'usuario_form.html', contexto)

@login_required
@user_passes_test(lambda user: user.is_staff)
def eliminar_usuario(request, pk):
    """Elimina (vía POST) un usuario por ID, si no es el usuario logueado."""
    
    usuario_a_eliminar = get_object_or_404(User, pk=pk)
    
    # Restricción: Evitar la auto-eliminación
    if usuario_a_eliminar.pk == request.user.pk:
        # Se redirige sin eliminar
        return redirect('listar_usuarios') 

    # Solo permitir la eliminación mediante POST
    if request.method == 'POST':
        try:
            usuario_a_eliminar.delete()
        except Exception:
            # Aquí podrías añadir un mensaje de error si la eliminación falla
            pass
            
    return redirect('listar_usuarios')

# ------------------------------------
# VISTAS DUMMY (TEMPORALES)
# ------------------------------------

@login_required
@user_passes_test(lambda user: user.is_staff)
def eliminar_cliente(request, pk):
    """Elimina (vía POST) un cliente por ID."""
    
    cliente_a_eliminar = get_object_or_404(Cliente, pk=pk)

    if request.method == 'POST':
        # Nota: Aquí deberías considerar si el cliente tiene ventas asociadas.
        # Por ahora, solo lo eliminamos directamente.
        try:
            cliente_a_eliminar.delete()
        except Exception:
            # Manejar error si no se puede eliminar (ej. por llave foránea)
            pass
            
    return redirect('listar_clientes')

@login_required
@user_passes_test(lambda user: user.is_staff)
def listar_clientes(request):
    """Muestra la tabla con todos los clientes registrados."""
    clientes = Cliente.objects.all().order_by('nombre_completo')
    
    contexto = {
        'clientes': clientes,
        'titulo_modulo': 'Gestión de Clientes',
    }
    return render(request, 'cliente_listado.html', contexto)
    
@login_required
@user_passes_test(lambda user: user.is_staff)
def cliente_form(request, pk=None):
    """
    Maneja la lógica de creación (pk=None) y edición (pk=ID) de clientes.
    """
    cliente = None
    if pk:
        # Modo Edición
        cliente = get_object_or_404(Cliente, pk=pk)
        titulo_form = f"Editar Cliente: {cliente.nombre_completo}"
    else:
        # Modo Creación
        titulo_form = "Registrar Nuevo Cliente"

    # Inicialización de datos para el formulario (Creación) o pre-relleno (Edición)
    datos_prev = {}
    if cliente:
        datos_prev = {
            'nombre_completo': cliente.nombre_completo,
            'cedula_ruc': cliente.cedula_ruc,
            'direccion': cliente.direccion,
            'telefono': cliente.telefono,
            'email': cliente.email,
        }
    
    mensaje = None
    es_error = False

    if request.method == 'POST':
        datos = request.POST
        
        # 1. Capturar datos
        nombre_completo = datos.get('nombre_completo', '').strip()
        cedula_ruc = datos.get('cedula_ruc', '').strip()
        direccion = datos.get('direccion', '').strip()
        telefono = datos.get('telefono', '').strip()
        email = datos.get('email', '').strip()

        # Actualizar datos_prev para repoblar el formulario en caso de error
        datos_prev = {
            'nombre_completo': nombre_completo,
            'cedula_ruc': cedula_ruc,
            'direccion': direccion,
            'telefono': telefono,
            'email': email,
        }

        # 2. Validaciones
        if not nombre_completo:
            mensaje = "Error: El nombre completo del cliente es obligatorio."
            es_error = True
        
        # Validación de unicidad de Nombre/RUC (excluyendo el objeto actual si estamos editando)
        elif Cliente.objects.filter(nombre_completo=nombre_completo).exclude(pk=pk).exists():
            mensaje = "Error: Ya existe un cliente con ese Nombre o Razón Social."
            es_error = True
        elif cedula_ruc and Cliente.objects.filter(cedula_ruc=cedula_ruc).exclude(pk=pk).exists():
            mensaje = "Error: Ya existe un cliente con ese número de Cédula/RUC."
            es_error = True

        else:
            try:
                # 3. Guardar o Actualizar
                if not cliente:
                    cliente = Cliente() # Crear nuevo objeto si no existe
                
                cliente.nombre_completo = nombre_completo
                cliente.cedula_ruc = cedula_ruc if cedula_ruc else None
                cliente.direccion = direccion
                cliente.telefono = telefono
                cliente.email = email
                
                cliente.save()
                
                # Redirigir al listado
                return redirect('listar_clientes') 
                
            except Exception as e:
                mensaje = f"Error interno al guardar el cliente: {e}"
                es_error = True

    contexto = {
        'cliente': cliente,
        'datos_prev': datos_prev,
        'mensaje': mensaje,
        'es_error': es_error,
        'titulo_form': titulo_form,
    }
    
    return render(request, 'cliente_form.html', contexto)

@login_required
def crear_venta(request):
    """
    Vista principal para registrar una nueva venta. 
    Maneja el formulario de cabecera, la lista dinámica de productos y la actualización de stock.
    """
    # 1. Obtener datos para los selectores del formulario
    clientes = Cliente.objects.all().order_by('nombre_completo')
    # Se obtienen todos los productos. La validación de stock se hará en JavaScript y en el POST.
    productos = Producto.objects.all().order_by('nombre') 
    
    mensaje = None
    es_error = False

    if request.method == 'POST':
        datos = request.POST
        
        # 2. Capturar datos de la Cabecera
        cliente_id = datos.get('cliente_id')
        
        # 3. Capturar datos de las Líneas de Detalle (los arrays que envía JavaScript)
        productos_ids = datos.getlist('producto_id[]')
        cantidades = datos.getlist('cantidad[]')
        precios_unitarios = datos.getlist('precio_unitario[]')
        
        if not cliente_id:
            mensaje = "Debe seleccionar un cliente para la venta."
            es_error = True
        elif not productos_ids:
            mensaje = "La venta debe contener al menos un producto."
            es_error = True
        else:
            try:
                # Utilizamos una transacción atómica para garantizar que si falla el stock, se revierta toda la venta.
                with transaction.atomic():
                    
                    # A. CREAR LA CABECERA DE LA VENTA
                    cliente = get_object_or_404(Cliente, pk=cliente_id)
                    
                    venta = Venta.objects.create(
                        cliente=cliente,
                        vendedor=request.user,
                        total=0.00 # Se actualizará en el paso C
                    )
                    
                    total_venta = 0.00
                    
                    # B. CREAR LOS DETALLES Y REGISTRAR MOVIMIENTOS
                    for i in range(len(productos_ids)):
                        prod_id = productos_ids[i]
                        cantidad_vendida = int(cantidades[i])
                        precio_unitario = float(precios_unitarios[i])
                        
                        producto = get_object_or_404(Producto, pk=prod_id)
                        
                        # Validar Stock antes de proceder
                        if cantidad_vendida <= 0 or cantidad_vendida > producto.stock:
                            raise ValueError(
                                f"Stock insuficiente: El producto '{producto.nombre}' solo tiene {producto.stock} unidades disponibles."
                            )
                            
                        subtotal_linea = cantidad_vendida * precio_unitario
                        total_venta += subtotal_linea
                        
                        # Crear la línea de DetalleVenta
                        DetalleVenta.objects.create(
                            venta=venta,
                            producto=producto,
                            cantidad=cantidad_vendida,
                            precio_unitario=precio_unitario,
                            subtotal=subtotal_linea
                        )
                        
                        # Registrar el MovimientoStock (Salida)
                        MovimientoStock.objects.create(
                            producto=producto,
                            cantidad= -cantidad_vendida, # Cantidad NEGATIVA para salida
                            tipo='SALIDA',
                            venta=venta,
                            usuario=request.user
                        )
                        
                        # ACTUALIZAR EL CAMPO 'stock' en el Producto (Usamos F() para seguridad)
                        producto.stock = F('stock') - cantidad_vendida
                        producto.save()
                        
                    # C. ACTUALIZAR EL TOTAL DE LA VENTA (Cabecera)
                    venta.total = total_venta
                    venta.save()
                    
                    # Redirigir a un mensaje de éxito (o al listado de ventas/ticket)
                    return redirect('listar_productos') # Redirección temporal a un listado existente

            except ValueError as ve:
                mensaje = f"Error de Stock/Validación: {ve}"
                es_error = True
            except Exception as e:
                mensaje = f"Error fatal al procesar la venta: {e}. Por favor, revise el log."
                es_error = True
                
    contexto = {
        'clientes': clientes,
        'productos': productos,
        'mensaje': mensaje,
        'es_error': es_error,
        'titulo_form': 'Crear Nueva Venta',
    }
    
    return render(request, 'venta_form.html', contexto)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import MovimientoStock

@login_required
def listar_movimientos(request):
    """Muestra el listado completo de entradas y salidas de stock."""
    
    # Obtener todos los movimientos ordenados por fecha descendente
    movimientos = MovimientoStock.objects.all().order_by('-fecha_movimiento')
    
    contexto = {
        'movimientos': movimientos,
        'titulo_modulo': 'Historial de Movimientos de Stock',
    }
    # NOTA: Necesitas crear la plantilla 'movimiento_listado.html'
    return render(request, 'movimiento_listado.html', contexto)


@login_required
def home_inventario(request):
    """
    Vista principal del dashboard que muestra un resumen de la actividad.
    """
    # 1. Obtener la última venta registrada
    try:
        # Usamos .latest() para obtener el objeto más reciente basado en 'fecha_venta'
        ultima_venta = Venta.objects.latest('fecha_venta')
    except Venta.DoesNotExist:
        ultima_venta = None
        
    # 2. Obtener el último producto (basado en id, asumiendo que los IDs son secuenciales)
    try:
        # .latest() también se puede usar con la PK si no hay un campo de fecha específico
        ultimo_producto = Producto.objects.latest('idProducto') 
    except Producto.DoesNotExist:
        ultimo_producto = None
        
    # 3. Obtener totales para el resumen (Opcional, pero bueno para el dashboard)
    total_ventas = Venta.objects.aggregate(Sum('total'))['total__sum'] or 0
    total_productos = Producto.objects.count()

    contexto = {
        'ultima_venta': ultima_venta,
        'ultimo_producto': ultimo_producto,
        'total_ventas': total_ventas,
        'total_productos': total_productos,
    }
    return render(request, 'home_inventario.html', contexto)