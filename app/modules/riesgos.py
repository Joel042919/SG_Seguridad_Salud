import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.utils.supabase_client import get_supabase_client
from app.auth import requerir_rol
import plotly.express as px
import random

def mostrar(usuario):
    """Módulo de Gestión de Riesgos (Ley 29783 Art. 26-28)"""
    requerir_rol(['admin', 'sst', 'supervisor'])
    
    st.title("⚠️ Gestión de Riesgos Laborales")
    
    tab1, tab2, tab3 = st.tabs([
        "📝 Registrar Riesgo (IPERC)",
        "📋 Matriz de Riesgos",
        "📊 Dashboard Ejecutivo"
    ])
    
    with tab1:
        registrar_riesgo(usuario)
    
    with tab2:
        listar_riesgos(usuario)
    
    with tab3:
        dashboard_riesgos()

def calcular_nivel(prob, sev):
    """Calcula nivel y etiqueta según matriz IPERC estándar"""
    producto = prob * sev
    if producto <= 6:
        return producto, "Riesgo Bajo"
    elif producto <= 12:
        return producto, "Riesgo Medio"
    else:
        return producto, "Riesgo Alto"

def registrar_riesgo(usuario):
    """Formulario dinámico de evaluación de riesgos"""
    
    st.subheader("Identificación de Peligros y Evaluación de Riesgos")
    st.caption("Complete la información para la matriz IPERC")
    
    supabase = get_supabase_client()
    
    # 1. Cargar Datos Maestros (Usuarios y Áreas)
    try:
        users_resp = supabase.table('usuarios').select('id, nombre_completo').eq('activo', True).execute()
        lista_usuarios = {u['nombre_completo']: u['id'] for u in users_resp.data} if users_resp.data else {}
        
        areas_resp = supabase.table('areas').select('area').execute()
        lista_areas = [a['area'] for a in areas_resp.data] if areas_resp.data else ["Producción", "Almacén", "Oficinas", "Mantenimiento"]
    except Exception as e:
        st.error(f"Error cargando maestros: {e}")
        return

    # --- NOTA IMPORTANTE: Eliminamos st.form para permitir interactividad en tiempo real ---
    
    # --- SECCIÓN 1: Identificación ---
    st.markdown("### 1. Identificación del Peligro")
    col1, col2 = st.columns(2)
    
    with col1:
        # Generador de código simple (simulado)
        cod_sufijo = datetime.now().strftime('%m%d%H%M')
        # Usamos key para mantener el estado si es necesario
        codigo = st.text_input("Código IPERC", value=f"RIE-GEN-{cod_sufijo}", key="risk_code")
        area = st.selectbox("Área", lista_areas, key="risk_area")
        puesto = st.text_input("Puesto de Trabajo", placeholder="Ej: Operario de Troqueladora", key="risk_puesto")
        
    with col2:
        actividad = st.text_area("Actividad / Tarea", placeholder="Descripción breve de la tarea", height=108, key="risk_act")
        
    col3, col4 = st.columns(2)
    with col3:
        peligro = st.text_input("Peligro", placeholder="Ej: Ruido excesivo, Piso resbaloso", key="risk_peligro")
    with col4:
        tipo_peligro = st.selectbox("Tipo de Peligro", 
            ["Físico", "Químico", "Biológico", "Ergonómico", "Mecánico", "Eléctrico", "Locativo", "Psicosocial"], key="risk_type")

    st.markdown("---")
    
    # --- SECCIÓN 2: Evaluación (Matriz) ---
    st.markdown("### 2. Evaluación de Riesgo Puro")
    st.caption("Ajuste los valores para ver el nivel de riesgo calculado en tiempo real.")
    
    c_prob, c_sev, c_res = st.columns([1, 1, 2])
    
    with c_prob:
        # Sliders interactivos (Inician en 1)
        prob = st.slider("Probabilidad (1-5)", 1, 5, 1, help="1: Muy Raro ... 5: Casi Seguro", key="risk_prob")
    with c_sev:
        sev = st.slider("Severidad (1-5)", 1, 5, 1, help="1: Insignificante ... 5: Catastrófico", key="risk_sev")
        
    # Cálculo en tiempo real (Ahora sí funciona porque no hay st.form bloqueándolo)
    nivel_val, nivel_txt = calcular_nivel(prob, sev)
    
    with c_res:
        # Mostramos el resultado dinámico
        if nivel_txt == "Riesgo Alto":
            st.error(f"🚨 **Nivel {nivel_val}: {nivel_txt}**\n\nRequiere controles inmediatos o paralización.")
        elif nivel_txt == "Riesgo Medio":
            st.warning(f"⚠️ **Nivel {nivel_val}: {nivel_txt}**\n\nRequiere medidas de mitigación y monitoreo.")
        else:
            st.success(f"✅ **Nivel {nivel_val}: {nivel_txt}**\n\nEl riesgo es tolerable, mantener controles básicos.")

    st.markdown("---")

    # --- SECCIÓN 3: Controles ---
    st.markdown("### 3. Medidas de Control")
    controles = st.text_area("Controles Actuales / Propuestos", placeholder="Ej: Uso de EPP, Guardas de seguridad...", key="risk_ctrl")
    
    col_resp, col_est = st.columns(2)
    with col_resp:
        nom_responsable = st.selectbox("Responsable de Implementación", options=list(lista_usuarios.keys()), key="risk_resp")
    with col_est:
        estado = st.selectbox("Estado de Implementación", ["pendiente", "en_mitigacion", "controlado"], key="risk_status")
        
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_eval = st.date_input("Fecha Evaluación", value=datetime.now(), key="risk_date1")
    with col_f2:
        prox_rev = st.date_input("Próxima Revisión", value=datetime.now() + timedelta(days=365), key="risk_date2")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botón de guardado fuera del form
    if st.button("💾 Registrar en Matriz IPERC", type="primary", use_container_width=True):
        if not puesto or not peligro:
            st.error("❌ Falta información obligatoria (Puesto o Peligro)")
            return
        
        # Preparar datos exactos para tu tabla
        datos_riesgo = {
            "codigo": codigo,
            "area": area,
            "puesto_trabajo": puesto,
            "actividad": actividad,
            "peligro": peligro,
            "tipo_peligro": tipo_peligro,
            "probabilidad": prob,
            "severidad": sev,
            # "nivel_riesgo": nivel_val,       # Calculado
            # "evaluacion_riesgo": nivel_txt,  # Texto calculado
            "controles_actuales": controles,
            "estado": estado,
            "responsable_id": lista_usuarios[nom_responsable], # UUID del usuario
            "fecha_evaluacion": fecha_eval.isoformat(),
            "proxima_revision": prox_rev.isoformat()
        }
        
        try:
            supabase.table('riesgos').insert(datos_riesgo).execute()
            st.success(f"✅ Riesgo {codigo} registrado correctamente")
            # Opcional: Limpiar campos recargando o usando session state, 
            # pero por simplicidad mostramos éxito.
        except Exception as e:
            st.error(f"Error al guardar en BD: {e}")

def listar_riesgos(usuario):
    """Vista de Matriz IPERC"""
    st.subheader("📋 Matriz de Riesgos (IPERC)")
    
    supabase = get_supabase_client()
    
    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtro_area = st.selectbox("Filtrar por Área", ["Todas"] + ["Producción", "Almacén", "Oficinas", "Mantenimiento", "Logística", "Seguridad", "Limpieza", "Comedor", "Laboratorio", "Exteriores"])
    with col_f2:
        filtro_nivel = st.selectbox("Nivel de Riesgo", ["Todos", "Riesgo Alto", "Riesgo Medio", "Riesgo Bajo"])
    
    # Query base
    query = supabase.table('riesgos').select('*')
    
    if filtro_area != "Todas":
        query = query.eq('area', filtro_area)
    if filtro_nivel != "Todos":
        query = query.eq('evaluacion_riesgo', filtro_nivel)
        
    riesgos = query.execute().data
    
    if not riesgos:
        st.info("No se encontraron registros con esos filtros.")
        return
        
    df = pd.DataFrame(riesgos)
    
    # Configuración de columnas para visualización profesional
    st.dataframe(
        df,
        use_container_width=True,
        column_order=[
            "codigo", "area", "puesto_trabajo", "peligro", "nivel_riesgo", 
            "evaluacion_riesgo", "estado", "proxima_revision"
        ],
        column_config={
            "codigo": "Cód.",
            "area": "Área",
            "puesto_trabajo": "Puesto",
            "peligro": "Peligro Identificado",
            "nivel_riesgo": st.column_config.NumberColumn(
                "Nivel (PxS)",
                help="Probabilidad x Severidad"
            ),
            "evaluacion_riesgo": st.column_config.TextColumn(
                "Evaluación",
                width="medium"
            ),
            "estado": st.column_config.SelectboxColumn(
                "Estado",
                options=["pendiente", "en_mitigacion", "controlado"],
                width="small"
            ),
            "proxima_revision": "Rev. Progr."
        },
        hide_index=True
    )
    
    # Botón descarga
    st.download_button(
        "📥 Descargar Matriz Excel/CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name=f"matriz_iperc_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

def dashboard_riesgos():
    """Dashboard Ejecutivo de Riesgos"""
    st.markdown("## 📊 Dashboard de Seguridad (IPERC)")
    st.markdown("---")
    
    supabase = get_supabase_client()
    data = supabase.table('riesgos').select('*').execute().data
    
    if not data:
        st.warning("No hay datos suficientes para el dashboard")
        return
        
    df = pd.DataFrame(data)
    
    # KPIs Superiores
    k1, k2, k3, k4 = st.columns(4)
    
    total = len(df)
    altos = len(df[df['evaluacion_riesgo'] == 'Riesgo Alto'])
    pendientes = len(df[df['estado'] == 'pendiente'])
    
    k1.metric("Total Riesgos Identificados", total, border=True)
    k2.metric("Riesgos Críticos (Altos)", altos, delta="Atención" if altos > 0 else "Ok", delta_color="inverse", border=True)
    k3.metric("Controles Pendientes", pendientes, delta="Requiere Acción" if pendientes > 0 else "Al día", delta_color="inverse", border=True)
    
    # Área con más riesgos
    area_top = df['area'].value_counts().idxmax() if not df.empty else "N/A"
    k4.metric("Área Más Crítica", area_top, border=True)
    
    st.markdown("### 📈 Análisis Gráfico")
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Gráfico de Pastel: Distribución por Nivel de Riesgo
        fig_pie = px.pie(
            df, 
            names='evaluacion_riesgo', 
            title='Distribución por Nivel de Riesgo',
            color='evaluacion_riesgo',
            color_discrete_map={
                'Riesgo Alto': '#ef4444',  # Rojo
                'Riesgo Medio': '#f59e0b', # Naranja
                'Riesgo Bajo': '#10b981'   # Verde
            },
            hole=0.4
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_g2:
        # Gráfico de Barras: Riesgos por Área y Estado
        fig_bar = px.bar(
            df, 
            x='area', 
            color='estado',
            title='Estado de Controles por Área',
            barmode='group',
            color_discrete_map={
                'pendiente': '#ef4444',
                'en_mitigacion': '#3b82f6',
                'controlado': '#10b981'
            }
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Mapa de Calor (Heatmap) Simulado con Scatter
    st.markdown("### 🔥 Mapa de Calor de Riesgos")
    fig_heat = px.density_heatmap(
        df, 
        x="probabilidad", 
        y="severidad", 
        z="nivel_riesgo", 
        nbinsx=5, 
        nbinsy=5,
        title="Concentración de Riesgos (Probabilidad vs Severidad)",
        text_auto=True,
        color_continuous_scale="Reds"
    )
    fig_heat.update_layout(xaxis_title="Probabilidad", yaxis_title="Severidad")
    st.plotly_chart(fig_heat, use_container_width=True)