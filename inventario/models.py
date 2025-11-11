# inventario/models.py

from django.db import models
from django.db.models import Sum # Necesario si decidimos calcular el stock dinámicamente
from django.contrib.auth.models import User # Usaremos el modelo User de Django para autenticación

# ----------------------------------------------------
# 1. Modelo CATEGORIA (Tabla: Categoria)
# ----------------------------------------------------
class Categoria(models.Model):
    idCategoria = models.AutoField(primary_key=True) # Clave primaria autoincremental
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre de la Categoría')

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre


# ----------------------------------------------------
# 2. Modelo PRODUCTO (Tabla: Producto)
# ----------------------------------------------------
class Producto(models.Model):
    idProducto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=200, verbose_name='Nombre del Producto')
    
    # Llave foránea a Categoria
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='Categoría'
    )
    
    stock = models.IntegerField(default=0, verbose_name='Stock Disponible') # Lo actualizaremos con MovimientoStock
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio de Venta')
    unidad_medida = models.CharField(max_length=50, default='Unidad', verbose_name='Unidad de Medida')
    
    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return self.nombre

# ----------------------------------------------------
# 3. Modelo CLIENTE (Tabla: Cliente)
# ----------------------------------------------------
class Cliente(models.Model):
    nombre_completo = models.CharField(max_length=150, unique=True, verbose_name='Nombre o Razón Social')
    cedula_ruc = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name='Cédula/RUC (Identificación)')
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name='Dirección')
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name='Teléfono')
    email = models.EmailField(max_length=100, blank=True, null=True, verbose_name='Email')
    
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nombre_completo']

    def __str__(self):
        return self.nombre_completo

# ----------------------------------------------------
# 4. Modelo VENTA (Cabecera)
# ----------------------------------------------------
class Venta(models.Model):
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.PROTECT, # No se puede eliminar un cliente si tiene ventas
        verbose_name='Cliente'
    )
    vendedor = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, # No se puede eliminar un usuario si tiene ventas registradas
        verbose_name='Vendedor (Usuario)'
    )
    
    fecha_venta = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Venta')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Total de la Venta')
    estado = models.CharField(max_length=50, default='Pagada', verbose_name='Estado')

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha_venta']

    def __str__(self):
        return f"Venta #{self.pk} - {self.cliente.nombre_completo}"

# ----------------------------------------------------
# 5. Modelo DETALLE DE VENTA (Líneas)
# ----------------------------------------------------
class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta, 
        on_delete=models.CASCADE, # Si se borra la cabecera, se borran los detalles
        related_name='detalles', 
        verbose_name='Venta'
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.PROTECT, 
        verbose_name='Producto'
    )
    
    cantidad = models.PositiveIntegerField(default=1, verbose_name='Cantidad')
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio Unitario al momento de la venta')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False, verbose_name='Subtotal')

    class Meta:
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Venta'
        unique_together = ('venta', 'producto') 

    def save(self, *args, **kwargs):
        """Calcula el subtotal antes de guardar."""
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

# ----------------------------------------------------
# 6. Modelo MOVIMIENTO DE STOCK
# ----------------------------------------------------
class MovimientoStock(models.Model):
    TIPO_MOVIMIENTO = [
        ('ENTRADA', 'Entrada (Compra, Ajuste Positivo)'),
        ('SALIDA', 'Salida (Venta, Ajuste Negativo)'),
    ]
    
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, verbose_name='Producto')
    # Usamos IntegerField ya que la cantidad puede ser positiva (entrada) o negativa (salida/merma)
    cantidad = models.IntegerField(verbose_name='Cantidad movida') 
    
    tipo = models.CharField(max_length=10, choices=TIPO_MOVIMIENTO, verbose_name='Tipo de Movimiento')
    
    # Referencia a Venta (si aplica)
    venta = models.ForeignKey(
        'Venta', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='Referencia de Venta'
    )
    
    fecha_movimiento = models.DateTimeField(auto_now_add=True, verbose_name='Fecha y Hora')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuario que registró')

    class Meta:
        verbose_name = 'Movimiento de Stock'
        verbose_name_plural = 'Movimientos de Stock'
        ordering = ['-fecha_movimiento']

    def __str__(self):
        signo = '+' if self.tipo == 'ENTRADA' else '-'
        return f"{self.fecha_movimiento.strftime('%Y-%m-%d')} | {self.producto.nombre}: {signo}{abs(self.cantidad)}"