import streamlit as st

# ⚠️ set_page_config SIEMPRE debe ser lo primero de Streamlit
st.set_page_config(
    page_title="MiMercadito",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Ahora sí los demás imports
import pandas as pd
from datetime import datetime, date
import database as db
import reportes as rp

# Inicializar BD
db.inicializar()

# Estado del carrito
if "carrito" not in st.session_state:
    st.session_state.carrito = []

# CSS
st.markdown("""
<style>
.main .block-container { padding-top: 1rem; padding-bottom: 2rem; }
.stButton > button { width: 100%; border-radius: 10px; font-weight: bold; }
div[data-testid="stMetricValue"] { color: #2E7D32; }
</style>
""", unsafe_allow_html=True)

st.title("🛒 MiMercadito")
st.caption(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")

tab_venta, tab_productos, tab_reportes, tab_historial = st.tabs(
    ["🧾 Vender", "📦 Productos", "📊 Reportes", "📜 Historial"]
)

# ============================================================
# VENDER
# ============================================================
with tab_venta:
    filtro = st.text_input("🔍 Buscar producto",
                           placeholder="Ej: papa, arroz, cebolla")

    productos = db.buscar_producto(filtro) if filtro else db.listar_productos()

    if not productos:
        st.warning("No hay productos. Ve a la pestaña **Productos** para agregar.")
    else:
        st.markdown("### Productos disponibles")
        cols = st.columns(3)
        for i, p in enumerate(productos):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{p['nombre']}**")
                    st.caption(f"S/ {p['precio_venta']:.2f} / {p['unidad']}")
                    st.caption(f"Stock: {p['stock']:.1f} {p['unidad']}")

                    cantidad = st.number_input(
                        "Cantidad",
                        min_value=0.1, value=1.0, step=0.5,
                        key=f"cant_{p['id']}",
                        label_visibility="collapsed"
                    )
                    if st.button("➕ Agregar", key=f"add_{p['id']}"):
                        existe = False
                        for item in st.session_state.carrito:
                            if item["id"] == p["id"]:
                                item["cantidad"] += cantidad
                                existe = True
                                break
                        if not existe:
                            st.session_state.carrito.append({
                                "id": p["id"],
                                "nombre": p["nombre"],
                                "cantidad": cantidad,
                                "precio": p["precio_venta"],
                                "unidad": p["unidad"],
                            })
                        st.rerun()

    st.divider()
    st.markdown("### 🛒 Carrito")

    if st.session_state.carrito:
        for idx, item in enumerate(st.session_state.carrito):
            col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
            with col1:
                st.write(f"**{item['nombre']}** — "
                         f"{item['cantidad']} {item['unidad']} × "
                         f"S/ {item['precio']:.2f}")
            with col2:
                st.write(f"S/ {item['cantidad'] * item['precio']:.2f}")
            with col3:
                if st.button("➖", key=f"menos_{idx}"):
                    item["cantidad"] -= 0.5
                    if item["cantidad"] <= 0:
                        st.session_state.carrito.pop(idx)
                    st.rerun()
            with col4:
                if st.button("❌", key=f"del_{idx}"):
                    st.session_state.carrito.pop(idx)
                    st.rerun()

        total = sum(i["cantidad"] * i["precio"]
                    for i in st.session_state.carrito)
        st.metric("💰 Total a cobrar", f"S/ {total:.2f}")

        col1, col2, col3 = st.columns(3)
        with col1:
            metodo = st.selectbox("Método de pago",
                                  ["efectivo", "yape", "plin", "transferencia"])
        with col2:
            cliente = st.text_input("Cliente (opcional)", "")
        with col3:
            st.write("")
            st.write("")
            if st.button("✅ COBRAR", type="primary"):
                db.registrar_venta(st.session_state.carrito,
                                   metodo_pago=metodo, cliente=cliente)
                st.success(f"✅ Venta registrada: S/ {total:.2f}")
                st.session_state.carrito = []
                st.rerun()

        if st.button("🗑️ Vaciar carrito"):
            st.session_state.carrito = []
            st.rerun()
    else:
        st.info("El carrito está vacío. Agrega productos arriba.")

# ============================================================
# PRODUCTOS
# ============================================================
with tab_productos:
    st.markdown("### ➕ Nuevo producto")

    with st.form("nuevo_producto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre")
            unidad = st.selectbox("Unidad", ["kg", "unidad", "litro", "docena"])
            precio_venta = st.number_input("Precio de venta (S/)",
                                           min_value=0.0, step=0.1)
        with c2:
            precio_compra = st.number_input("Precio de compra (S/)",
                                            min_value=0.0, step=0.1)
            stock = st.number_input("Stock inicial", min_value=0.0, step=1.0)
            stock_minimo = st.number_input("Stock mínimo",
                                           min_value=0.0, value=5.0)

        enviado = st.form_submit_button("💾 Guardar producto", type="primary")
        if enviado:
            if not nombre:
                st.error("El nombre es obligatorio")
            elif db.agregar_producto(nombre, precio_venta, unidad,
                                     precio_compra, stock, stock_minimo):
                st.success(f"✅ Producto '{nombre}' agregado")
                st.rerun()
            else:
                st.error("Ese producto ya existe")

    st.divider()
    st.markdown("### 📋 Lista de productos")

    productos = db.listar_productos()
    if productos:
        df = pd.DataFrame(productos)
        df = df[["id", "nombre", "unidad", "precio_compra",
                 "precio_venta", "stock", "stock_minimo"]]
        df.columns = ["ID", "Nombre", "Unidad", "P. Compra",
                      "P. Venta", "Stock", "Stock mín."]
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("#### ✏️ Editar o eliminar")
        opciones = {f"{p['id']} - {p['nombre']}": p for p in productos}
        sel = st.selectbox("Selecciona un producto", list(opciones.keys()))
        if sel:
            p = opciones[sel]
            with st.form("editar"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    nuevo_precio = st.number_input(
                        "Precio venta", value=float(p["precio_venta"]),
                        min_value=0.0, step=0.1)
                    nuevo_stock = st.number_input(
                        "Stock", value=float(p["stock"]),
                        min_value=0.0, step=1.0)
                with c2:
                    nuevo_pc = st.number_input(
                        "Precio compra", value=float(p["precio_compra"]),
                        min_value=0.0, step=0.1)
                    nuevo_sm = st.number_input(
                        "Stock mínimo", value=float(p["stock_minimo"]),
                        min_value=0.0, step=1.0)
                with c3:
                    nueva_unidad = st.selectbox(
                        "Unidad", ["kg", "unidad", "litro", "docena"],
                        index=["kg", "unidad", "litro",
                               "docena"].index(p["unidad"])
                        if p["unidad"] in ["kg", "unidad", "litro", "docena"] else 0
                    )

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.form_submit_button("💾 Actualizar", type="primary"):
                        db.actualizar_producto(
                            p["id"],
                            precio_venta=nuevo_precio,
                            precio_compra=nuevo_pc,
                            stock=nuevo_stock,
                            stock_minimo=nuevo_sm,
                            unidad=nueva_unidad
                        )
                        st.success("Actualizado")
                        st.rerun()
                with col_b:
                    if st.form_submit_button("🗑️ Eliminar"):
                        db.eliminar_producto(p["id"])
                        st.warning("Eliminado")
                        st.rerun()
    else:
        st.info("Aún no hay productos registrados.")

# ============================================================
# REPORTES
# ============================================================
with tab_reportes:
    st.markdown("### 📊 Reportes")

    opcion = st.radio("Rango",
                      ["Hoy", "Últimos 7 días", "Este mes", "Personalizado"],
                      horizontal=True)

    hoy = date.today()
    if opcion == "Hoy":
        desde = hasta = hoy
    elif opcion == "Últimos 7 días":
        desde = date.fromordinal(hoy.toordinal() - 6)
        hasta = hoy
    elif opcion == "Este mes":
        desde = hoy.replace(day=1)
        hasta = hoy
    else:
        c1, c2 = st.columns(2)
        with c1:
            desde = st.date_input("Desde", hoy)
        with c2:
            hasta = st.date_input("Hasta", hoy)

    ventas = db.ventas_rango(str(desde), str(hasta))
    detalles = {v["id"]: db.detalle_venta(v["id"]) for v in ventas}
    top = db.productos_mas_vendidos()
    metodos = db.resumen_metodos_pago(str(hasta))

    total = sum(v["total"] for v in ventas)
    n = len(ventas)
    prom = total / n if n else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total vendido", f"S/ {total:.2f}")
    c2.metric("🧾 N ventas", n)
    c3.metric("📊 Ticket promedio", f"S/ {prom:.2f}")

    st.markdown("#### 🏆 Top productos")
    if top:
        df_top = pd.DataFrame(top)
        df_top.columns = ["Producto", "Cantidad", "Ingreso (S/)"]
        st.dataframe(df_top, use_container_width=True, hide_index=True)
    else:
        st.info("Sin ventas aún")

    st.markdown("#### 💳 Métodos de pago")
    if metodos:
        df_m = pd.DataFrame(metodos)
        df_m.columns = ["Método", "N ventas", "Total (S/)"]
        st.dataframe(df_m, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### 📤 Exportar")

    c1, c2 = st.columns(2)
    with c1:
        excel = rp.generar_excel(ventas, detalles)
        st.download_button(
            "📊 Descargar Excel",
            data=excel,
            file_name=f"reporte_{desde}_{hasta}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with c2:
        imagen = rp.generar_imagen(ventas, top, metodos)
        st.download_button(
            "🖼️ Descargar Imagen",
            data=imagen,
            file_name=f"reporte_{desde}_{hasta}.png",
            mime="image/png",
            use_container_width=True
        )

    with st.expander("👁️ Ver vista previa del reporte"):
        st.image(imagen)

# ============================================================
# HISTORIAL
# ============================================================
with tab_historial:
    st.markdown("### 📜 Historial de ventas")

    ventas = db.ventas_del_dia()
    if ventas:
        for v in ventas:
            with st.expander(
                f"Venta #{v['id']} — S/ {v['total']:.2f} — "
                f"{v['metodo_pago']} — {v['fecha'][:16]}"
            ):
                detalles = db.detalle_venta(v["id"])
                if detalles:
                    df = pd.DataFrame(detalles)
                    df = df[["nombre", "cantidad",
                             "precio_unitario", "subtotal"]]
                    df.columns = ["Producto", "Cantidad", "P. Unit", "Subtotal"]
                    st.dataframe(df, use_container_width=True,
                                 hide_index=True)
                if v.get("cliente"):
                    st.caption(f"👤 Cliente: {v['cliente']}")
    else:
        st.info("No hay ventas registradas hoy.")
