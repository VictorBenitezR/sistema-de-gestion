# inventario/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ------------------------------------
    # Rutas de Autenticación
    # ------------------------------------
    path('registro/', views.registrar_usuario, name='registrar_usuario'),
    path('login/', views.login_usuario, name='login_usuario'),
    path('logout/', views.logout_usuario, name='logout_usuario'), 
    
    # ------------------------------------
    # Ruta del Dashboard
    # ------------------------------------
    path('', views.home_inventario, name='home_inventario'),
    
    # ------------------------------------
    # Gestión de Categorías
    # ------------------------------------
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/', views.listar_categorias, name='listar_categorias'),
    path('categorias/eliminar/<int:pk>/', views.eliminar_categoria, name='eliminar_categoria'),
    path('categorias/editar/<int:pk>/', views.editar_categoria, name='editar_categoria'),

    # ------------------------------------
    # Gestión de Productos
    # ------------------------------------
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('productos/', views.listar_productos, name='listar_productos'),
    path('productos/eliminar/<int:pk>/', views.eliminar_producto, name='eliminar_producto'),
    path('productos/editar/<int:pk>/', views.editar_producto, name='editar_producto'),

    # ------------------------------------
    # Gestión de Usuarios (Ya implementado)
    # ------------------------------------
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('usuarios/editar/<int:pk>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/eliminar/<int:pk>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('ventas/crear/', views.crear_venta, name='crear_venta'),  
    path('movimientos/', views.listar_movimientos, name='listar_movimientos'), 
    path('clientes/', views.listar_clientes, name='listar_clientes'), # Actualizada
    path('clientes/crear/', views.cliente_form, name='crear_cliente'), # Nueva
    path('clientes/editar/<int:pk>/', views.cliente_form, name='editar_cliente'), # Nueva
    path('clientes/eliminar/<int:pk>/', views.eliminar_cliente, name='eliminar_cliente'), # Nueva
]