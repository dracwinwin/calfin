import sqlite3
from datetime import datetime

DB = "mercadito.db"

def conectar():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar():
    conn = conectar()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            unidad TEXT DEFAULT 'kg',
            precio_compra REAL DEFAULT 0,
            precio_venta REAL NOT NULL,
            stock REAL DEFAULT 0,
            stock_minimo REAL DEFAULT 5
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            total REAL NOT NULL,
            metodo_pago TEXT DEFAULT 'efectivo',
            cliente TEXT DEFAULT ''
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS venta_detalle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            nombre TEXT,
            cantidad REAL,
            precio_unitario REAL,
            subtotal REAL,
            FOREIGN KEY(venta_id) REFERENCES ventas(id)
        )
    """)
    conn.commit()
    conn.close()

def agregar_producto(nombre, precio_venta, unidad="kg",
                     precio_compra=0, stock=0, stock_minimo=5):
    conn = conectar()
    try:
        conn.execute(
            "INSERT INTO productos (nombre, unidad, precio_compra, "
            "precio_venta, stock, stock_minimo) VALUES (?,?,?,?,?,?)",
            (nombre, unidad, precio_compra, precio_venta, stock, stock_minimo)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def listar_productos():
    conn = conectar()
    filas = conn.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
    conn.close()
    return [dict(f) for f in filas]

def buscar_producto(texto):
    conn = conectar()
    filas = conn.execute(
        "SELECT * FROM productos WHERE nombre LIKE ? ORDER BY nombre",
        (f"%{texto}%",)
    ).fetchall()
    conn.close()
    return [dict(f) for f in filas]

def actualizar_producto(pid, **campos):
    if not campos:
        return
    sets = ", ".join(f"{k} = ?" for k in campos)
    vals = list(campos.values()) + [pid]
    conn = conectar()
    conn.execute(f"UPDATE productos SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()

def eliminar_producto(pid):
    conn = conectar()
    conn.execute("DELETE FROM productos WHERE id = ?", (pid,))
    conn.commit()
    conn.close()

def registrar_venta(items, metodo_pago="efectivo", cliente=""):
    conn = conectar()
    c = conn.cursor()
    total = sum(i["cantidad"] * i["precio"] for i in items)
    c.execute(
        "INSERT INTO ventas (fecha, total, metodo_pago, cliente) "
        "VALUES (?,?,?,?)",
        (datetime.now().isoformat(), total, metodo_pago, cliente)
    )
    venta_id = c.lastrowid
    for it in items:
        c.execute(
            "INSERT INTO venta_detalle "
            "(venta_id, producto_id, nombre, cantidad, "
            "precio_unitario, subtotal) VALUES (?,?,?,?,?,?)",
            (venta_id, it["id"], it["nombre"], it["cantidad"],
             it["precio"], it["cantidad"] * it["precio"])
        )
        c.execute(
            "UPDATE productos SET stock = stock - ? WHERE id = ?",
            (it["cantidad"], it["id"])
        )
    conn.commit()
    conn.close()
    return total

def ventas_del_dia(fecha=None):
    if fecha is None:
        fecha = datetime.now().strftime("%Y-%m-%d")
    conn = conectar()
    filas = conn.execute(
        "SELECT * FROM ventas WHERE date(fecha) = ? ORDER BY fecha DESC",
        (fecha,)
    ).fetchall()
    conn.close()
    return [dict(f) for f in filas]

def ventas_rango(desde, hasta):
    conn = conectar()
    filas = conn.execute(
        "SELECT * FROM ventas WHERE date(fecha) BETWEEN ? AND ? "
        "ORDER BY fecha DESC",
        (desde, hasta)
    ).fetchall()
    conn.close()
    return [dict(f) for f in filas]

def detalle_venta(venta_id):
    conn = conectar()
    filas = conn.execute(
        "SELECT * FROM venta_detalle WHERE venta_id = ?", (venta_id,)
    ).fetchall()
    conn.close()
    return [dict(f) for f in filas]

def productos_mas_vendidos(limite=10):
    conn = conectar()
    filas = conn.execute("""
        SELECT nombre, SUM(cantidad) AS total_cant,
               SUM(subtotal) AS total_ingreso
        FROM venta_detalle
        GROUP BY nombre
        ORDER BY total_cant DESC
        LIMIT ?
    """, (limite,)).fetchall()
    conn.close()
    return [dict(f) for f in filas]

def resumen_metodos_pago(fecha=None):
    if fecha is None:
        fecha = datetime.now().strftime("%Y-%m-%d")
    conn = conectar()
    filas = conn.execute("""
        SELECT metodo_pago, COUNT(*) AS n, SUM(total) AS total
        FROM ventas WHERE date(fecha) = ?
        GROUP BY metodo_pago
    """, (fecha,)).fetchall()
    conn.close()
    return [dict(f) for f in filas]
