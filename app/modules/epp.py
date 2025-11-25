import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.utils.supabase_client import get_supabase_client
from app.utils.storage_helper import subir_archivo_storage
from app.auth import requerir_rol
import plotly.express as px

def mostrar(usuario):
    """Módulo de Gestión de EPP (Ley 29783 Art. 29)"""
    requerir_rol(['admin', 'sst', 'supervisor'])
    
    st.title("🛡️ Gestión de Equipos de Protección Personal (EPP)")
    
    tab1, tab2, tab3 = st.tabs([
        "📊 Dashboard & Inventario",
        "👤 Asignar EPP",
        "📦 Catálogo Maestro"
    ])
    
    with tab1:
        dashboard_epp(usuario)
    
    with tab2:
        asignar_epp(usuario)
    
    with tab3:
        gestionar_catalogo(usuario)

# ------------------------------
# Dashboard
# ------------------------------
def dashboard_epp(usuario):
    st.markdown("### Estado de Asignaciones")
    sup = get_supabase_client()

    query = sup.table('epp_asignaciones').select(
        '*, epp_catalogo(nombre, vida_util_meses), usuarios(nombre_completo, area)'
    ).execute()

    if not query.data:
        st.info("No hay asignaciones registradas."); return

    df = pd.DataFrame(query.data)
    df['Equipo'] = df['epp_catalogo'].apply(lambda x: x['nombre'] if x else 'N/A')
    df['Trabajador'] = df['usuarios'].apply(lambda x: x['nombre_completo'] if x else 'N/A')
    df['Área'] = df['usuarios'].apply(lambda x: x['area'] if x else 'N/A')

    hoy = datetime.now().date()
    df['vencimiento_dt'] = pd.to_datetime(df['fecha_vencimiento']).dt.date

    def get_estado_real(row):
        if row['vencimiento_dt'] < hoy:
            return "Vencido"
        elif row['vencimiento_dt'] <= hoy + timedelta(days=30):
            return "Por Vencer (<30 días)"
        else:
            return "Vigente"

    df['Estado Real'] = df.apply(get_estado_real, axis=1)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Asignados", len(df), border=True)

    vencidos = len(df[df['Estado Real'] == 'Vencido'])
    por_vencer = len(df[df['Estado Real'] == 'Por Vencer (<30 días)'])

    k2.metric("Vencidos", vencidos, delta="-Renovar" if vencidos > 0 else "Ok", delta_color="inverse", border=True)
    k3.metric("Por Vencer (30d)", por_vencer, delta="Atención" if por_vencer > 0 else "Ok", delta_color="inverse", border=True)

    top_epp = df['Equipo'].mode()[0] if not df.empty else "N/A"
    k4.metric("EPP Más Usado", top_epp, border=True)

    c1, c2 = st.columns(2)
    with c1:
        fig_est = px.pie(df, names='Estado Real', title='Estado de EPPs Asignados',
                         color='Estado Real',
                         color_discrete_map={'Vencido': 'red', 'Por Vencer (<30 días)': 'orange', 'Vigente': 'green'})
        st.plotly_chart(fig_est, use_container_width=True)

    with c2:
        fig_area = px.bar(df, x='Área', color='Estado Real', title='Distribución por Área', barmode='group')
        st.plotly_chart(fig_area, use_container_width=True)

    st.markdown("### 📋 Detalle de Asignaciones")

    filtro_est = st.multiselect("Filtrar por Estado", ["Vigente", "Vencido", "Por Vencer (<30 días)"])
    if filtro_est:
        df = df[df['Estado Real'].isin(filtro_est)]

    st.dataframe(
        df[['Trabajador', 'Área', 'Equipo', 'fecha_entrega', 'fecha_vencimiento', 'Estado Real']],
        use_container_width=True,
        column_config={
            "fecha_entrega": "Entrega",
            "fecha_vencimiento": "Vence",
            "Estado Real": st.column_config.TextColumn("Estado", width="medium")
        },
        hide_index=True
    )

# ------------------------------
# Asignar EPP
# ------------------------------
def asignar_epp(usuario):
    st.subheader("👤 Nueva Asignación de EPP")
    sup = get_supabase_client()

    users = sup.table('usuarios').select('id, nombre_completo, area').eq('activo', True).execute().data
    items = sup.table('epp_catalogo').select('id, nombre, vida_util_meses').execute().data

    if not users or not items:
        st.warning("Faltan datos maestros (usuarios o catálogo)"); return

    dict_users = {f"{u['nombre_completo']} ({u['area']})": u for u in users}
    dict_items = {i['nombre']: i for i in items}

    with st.form("form_asignar_epp"):
        col1, col2 = st.columns(2)
        with col1:
            sel_user_key = st.selectbox("Trabajador", options=dict_users.keys())
            user_data = dict_users[sel_user_key]
        with col2:
            sel_item_key = st.selectbox("Equipo de Protección", options=dict_items.keys())
            item_data = dict_items[sel_item_key]

        col3, col4 = st.columns(2)
        with col3:
            f_entrega = st.date_input("Fecha de Entrega", value=datetime.now())
        meses_vida = item_data['vida_util_meses'] or 12
        f_vence_calc = f_entrega + timedelta(days=meses_vida * 30)
        with col4:
            f_vence = st.date_input("Fecha de Vencimiento (Calc)", value=f_vence_calc)
            st.caption(f"Vida útil estimada: {meses_vida} meses")

        if st.form_submit_button("💾 Registrar Entrega", type="primary"):
            datos = {
                "trabajador_id": user_data['id'],
                "epp_id": item_data['id'],
                "fecha_entrega": f_entrega.isoformat(),
                "fecha_vencimiento": f_vence.isoformat(),
                "estado": "activo"
            }
            try:
                sup.table('epp_asignaciones').insert(datos).execute()
                st.success(f"✅ {sel_item_key} asignado correctamente a {user_data['nombre_completo']}")
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ------------------------------
# Catálogo Maestro
# ------------------------------
def gestionar_catalogo(usuario):
    st.subheader("📦 Catálogo Maestro de EPPs")
    sup = get_supabase_client()

    with st.expander("➕ Agregar Nuevo Producto al Catálogo"):
        with st.form("new_epp"):
            c1, c2 = st.columns([3, 1])
            with c1:
                nombre = st.text_input("Nombre del EPP")
                desc = st.text_input("Descripción Técnica")
            with c2:
                vida = st.number_input("Vida Útil (Meses)", min_value=1, value=12)
                cert = st.text_input("Certificación (ANSI/ISO)")

            if st.form_submit_button("Guardar Producto"):
                try:
                    sup.table('epp_catalogo').insert({
                        "nombre": nombre,
                        "descripcion": desc,
                        "certificacion": cert,
                        "vida_util_meses": vida
                    }).execute()
                    st.success("Producto agregado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    items = sup.table('epp_catalogo').select('*').order('id').execute().data
    if items:
        st.dataframe(
            pd.DataFrame(items),
            use_container_width=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "nombre": "Producto",
                "vida_util_meses": st.column_config.NumberColumn("Vida (Meses)", format="%d m"),
                "certificacion": "Norma"
            },
            hide_index=True
        )