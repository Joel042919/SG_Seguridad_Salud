import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from app.utils.supabase_client import get_supabase_client
from app.auth import requerir_rol
import json
import os
import requests

def mostrar(usuario):
    """Módulo de Capacitaciones y Concientización (Ley 29783 Art. 31)"""
    requerir_rol(['admin', 'sst', 'supervisor', 'gerente'])
    
    st.title("🎓 Gestión de Capacitaciones SST")
    
    # Tabs principales
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📅 Programar Capacitación",
        "👥 Gestionar Asistentes",
        "📤 Material de Capacitación",
        "📋 Encuestas Post-Capacitación",
        "📊 Reporte de Efectividad"
    ])
    
    with tab1:
        programar_capacitacion(usuario)
    
    with tab2:
        gestionar_asistentes(usuario)
    
    with tab3:
        gestionar_material(usuario)
    
    with tab4:
        encuestas_post_capacitacion(usuario)
    
    with tab5:
        reporte_efectividad(usuario)

def programar_capacitacion(usuario):
    """Programar nueva capacitación"""
    
    st.subheader("📅 Programar Nueva Capacitación")
    
    with st.form("form_capacitacion", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            codigo = st.text_input(
                "Código",
                value=f"CAP-{datetime.now().strftime('%Y%m%d')}",
                help="Debe ser único"
            )
            
            tema = st.text_input("Tema de Capacitación")
            
            areas = ["Producción", "Almacén", "Oficinas", "Mantenimiento", "Seguridad"]
            area_seleccionada = st.multiselect("Área(s) Destino", areas)
        
        with col2:
            fecha_programada = st.date_input("Fecha", min_value=datetime.now().date())
            hora = st.time_input("Hora", value=datetime.strptime("09:00", "%H:%M").time())
            
            duracion_horas = st.number_input("Duración (horas)", min_value=1, value=2, step=1)
            
        instructor = st.text_input("Instructor", value=usuario['nombre_completo'])
        
        # --- ELIMINADO: Input de Link Material ---
        
        st.info("ℹ️ Los recordatorios (24h y 1h antes) se gestionan automáticamente por el sistema.")

        submitted = st.form_submit_button("📅 Programar", type="primary")
        
        if submitted:
            if not tema or not codigo:
                st.error("❌ Faltan datos obligatorios (Tema o Código)")
                return

            fecha_hora = datetime.combine(fecha_programada, hora)
            
            # Preparar datos
            capacitacion_data = {
                'codigo': codigo,
                'tema': tema,
                'area_destino': ", ".join(area_seleccionada), 
                'fecha_programada': fecha_hora.isoformat(),
                'duracion_horas': duracion_horas,
                'instructor': instructor,
                'estado': 'programada'
            }
            
            # --- ELIMINADO: Lógica de agregar material_url ---

            # Guardar en BD
            result = guardar_capacitacion(capacitacion_data)
            
            if result:
                # Nota: Mantengo tu lógica de webhook existente en este archivo
                webhook_url = os.getenv("N8N_WEBHOOK_URL_CAPACITACION")
                if webhook_url:
                    try:
                        requests.post(
                            f"{webhook_url}/capacitacion-programada",
                            json={
                                "capacitacion_id": result["id"],
                                "codigo": result["codigo"],
                                "tema": result["tema"],
                                "fecha": result["fecha_programada"],
                                "area": result.get("area_destino", "")
                            },
                            timeout=5
                        )
                    except Exception as e:
                        st.warning(f"⚠️ No se pudo notificar a n8n: {e}")
                st.success(f"✅ Capacitación {result['codigo']} creada y flujo activado")

def guardar_capacitacion(data):
    """Guarda en Supabase"""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('capacitaciones').insert(data).execute()
        
        if response.data:
            cap = response.data[0]
            return cap
    except Exception as e:
        st.error(f"Error guardando capacitación: {e}")
    
    return None

def gestionar_asistentes(usuario):
    """Gestionar lista de asistentes y registro de asistencia"""
    
    st.subheader("👥 Gestionar Asistentes a Capacitaciones")
    
    supabase = get_supabase_client()
    
    # Cargar capacitaciones programadas
    capacitaciones = supabase.table('capacitaciones').select(
        '*, asistentes_capacitacion(*, usuarios(*))'
    ).eq('estado', 'programada').execute().data
    
    if not capacitaciones:
        st.info("ℹ️ No hay capacitaciones programadas")
        return
    
    # Seleccionar capacitación
    cap_seleccionada = st.selectbox(
        "Seleccionar Capacitación",
        options=capacitaciones,
        format_func=lambda x: f"{x['codigo']} - {x['tema'][:50]}... ({x['fecha_programada']})"
    )
    
    if not cap_seleccionada:
        return
    
    # Mostrar detalles
    with st.expander("📋 Detalles de la Capacitación", expanded=True):
        st.json({
            "Código": cap_seleccionada['codigo'],
            "Tema": cap_seleccionada['tema'],
            "Fecha": cap_seleccionada['fecha_programada'],
            "Instructor": cap_seleccionada['instructor']
        })
    
    # Cargar trabajadores disponibles
    trabajadores = supabase.table('usuarios').select(
        'id', 'nombre_completo', 'area', 'rol'
    ).eq('activo', True).neq('rol', 'admin').execute().data
    
    if not trabajadores:
        st.warning("⚠️ No hay trabajadores activos")
        return
    
    df_trabajadores = pd.DataFrame(trabajadores)
    
    # Tabla de asistentes actuales
    st.markdown("### 📋 Asistentes Asignados")
    
    asistentes_actuales = cap_seleccionada.get('asistentes_capacitacion', [])
    
    if asistentes_actuales:
        df_asistentes = pd.DataFrame([
            {
                'ID': a['trabajador_id'],
                'Nombre': a['usuarios']['nombre_completo'],
                'Asistió': a['asistio'],
                'Calificación': a.get('calificacion', 'N/A')
            } for a in asistentes_actuales
        ])
        
        st.dataframe(df_asistentes, use_container_width=True)
        
        # Botón para descargar lista
        excel_data = df_asistentes.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Descargar Lista CSV",
            excel_data,
            f"asistentes_{cap_seleccionada['codigo']}.csv",
            "text/csv"
        )
    else:
        st.info("ℹ️ Los recordatorios (24 h y 1 h antes) y el formulario de encuesta post-capacitación se envían automáticamente sin necesidad de guardar nuevamente.")
    
    # Agregar nuevos asistentes
    st.markdown("### ➕ Agregar Asistentes")
    
    # Filtrar trabajadores sugeridos por área
    raw_areas = cap_seleccionada.get('area_destino') or ''
    area_capacitacion = [a.strip() for a in raw_areas.split(',') if a.strip()]
    
    if area_capacitacion:
        trabajadores_filtrados = df_trabajadores[df_trabajadores['area'].isin(area_capacitacion)]
    else:
        trabajadores_filtrados = df_trabajadores
    
    nuevos_asistentes = st.multiselect(
        "Seleccionar Trabajadores",
        options=trabajadores_filtrados['id'].tolist(),
        format_func=lambda x: f"{df_trabajadores[df_trabajadores['id'] == x]['nombre_completo'].iloc[0]} ({df_trabajadores[df_trabajadores['id'] == x]['area'].iloc[0]})"
    )
    
    if nuevos_asistentes:
        if st.button("📅 Agregar Asistentes Seleccionados", type="primary"):
            agregar_asistentes(cap_seleccionada['id'], nuevos_asistentes)
            st.success(f"✅ {len(nuevos_asistentes)} asistentes agregados")
            st.rerun()
    
    # Registrar asistencia el día de la capacitación
    st.markdown("### ✅ Registrar Asistencia")
    
    # Validación simple de fecha (compara solo fechas, ignora hora)
    fecha_prog = pd.to_datetime(cap_seleccionada['fecha_programada']).date()
    hoy = datetime.now().date()
    
    if hoy >= fecha_prog: # Permitir marcar asistencia el día o después
        for asistente in asistentes_actuales:
            with st.expander(f"📝 {asistente['usuarios']['nombre_completo']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    asistio = st.checkbox(
                        "Asistió",
                        value=asistente['asistio'],
                        key=f"asist_{asistente['id']}"
                    )
                
                with col2:
                    calificacion = st.number_input(
                        "Calificación (1-5)",
                        min_value=1, max_value=5,
                        value=asistente.get('calificacion', 3) or 3,
                        key=f"calif_{asistente['id']}"
                    )
                
                feedback = st.text_area(
                    "Feedback del Asistente",
                    value=asistente.get('feedback', '') or '',
                    key=f"feed_{asistente['id']}"
                )
                
                if st.button("💾 Guardar Asistencia", key=f"save_{asistente['id']}"):
                    actualizar_asistencia(
                        asistente['id'],
                        asistio,
                        calificacion,
                        feedback
                    )
                    st.success("✅ Asistencia registrada")
    else:
        st.info(f"ℹ️ Podrás registrar asistencia a partir del {fecha_prog}.")

def agregar_asistentes(capacitacion_id, trabajador_ids):
    """Agregar múltiples asistentes a capacitación"""
    supabase = get_supabase_client()
    try:
        data_to_insert = [
            {'capacitacion_id': capacitacion_id, 'trabajador_id': tid, 'asistio': False}
            for tid in trabajador_ids
        ]
        supabase.table('asistentes_capacitacion').insert(data_to_insert).execute()
    except Exception as e:
        st.error(f"Error agregando asistentes: {e}")

def actualizar_asistencia(asistente_id, asistio, calificacion, feedback):
    """Actualizar registro de asistencia y notificar"""
    supabase = get_supabase_client()
    
    try:
        supabase.table('asistentes_capacitacion').update({
            'asistio': asistio,
            'calificacion': calificacion,
            'feedback': feedback
            # No actualizamos fecha_asistencia si no está en tu esquema, 
            # si está, descomenta la siguiente línea:
            # 'fecha_asistencia': datetime.now().isoformat() if asistio else None
        }).eq('id', asistente_id).execute()
                    
    except Exception as e:
        st.error(f"Error actualizando asistencia: {e}")

def gestionar_material(usuario):
    """Gestionar material de capacitación vía URLs externas"""
    st.subheader("📤 Material de Capacitación")

    supabase = get_supabase_client()

    capacitaciones = supabase.table('capacitaciones').select('id', 'codigo', 'tema').execute().data
    if not capacitaciones:
        st.warning("⚠️ No hay capacitaciones para gestionar material")
        return

    cap_seleccionada = st.selectbox(
        "Seleccionar Capacitación",
        options=capacitaciones,
        format_func=lambda x: f"{x['codigo']} - {x['tema']}"
    )
    if not cap_seleccionada:
        return

    with st.form("form_material_url", clear_on_submit=True):
        tipo_material = st.selectbox("Tipo", ["Presentación", "Guía", "Evaluación", "Video", "Otros"])
        descripcion = st.text_input("Descripción")
        url_material = st.text_input(
            "URL del material (Drive, YouTube, SharePoint, PDF online, etc.)",
            placeholder="https://..."
        )
        submitted = st.form_submit_button("🔗 Agregar Material", type="primary")

        if submitted:
            if not url_material.strip():
                st.error("❌ Debes pegar una URL válida")
            else:
                try:
                    supabase.table('material_capacitacion').insert({
                        'capacitacion_id': cap_seleccionada['id'],
                        'tipo': tipo_material,
                        'descripcion': descripcion or 'Material externo',
                        'archivo_url': url_material.strip(),
                        'subido_por': usuario['id']
                    }).execute()
                    st.success("✅ Enlace agregado exitosamente")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    # Listar material existente
    st.divider()
    st.markdown("### 📚 Material Actual")
    material = supabase.table('material_capacitacion').select('*').eq('capacitacion_id', cap_seleccionada['id']).execute().data
    if material:
        for item in material:
            with st.expander(f"{item['tipo']} - {item.get('descripcion', '')}"):
                st.markdown(f"[📎 Abrir enlace]({item['archivo_url']})")
                if st.button("🗑️ Eliminar", key=f"del_{item['id']}"):
                    # No borramos archivo (está afuera), solo BD
                    supabase.table('material_capacitacion').delete().eq('id', item['id']).execute()
                    st.success("Enlace eliminado")
                    st.rerun()
    else:
        st.info("ℹ️ No hay material registrado aún")

def eliminar_material(material_id, archivo_url):
    """Eliminar material"""
    supabase = get_supabase_client()
    try:
        from app.utils.storage_helper import eliminar_archivo_storage
        # Solo intentamos borrar de storage si parece un archivo de storage (no video de youtube)
        if "supabase.co" in archivo_url:
            eliminar_archivo_storage(archivo_url, 'sst-documentos')
        
        supabase.table('material_capacitacion').delete().eq('id', material_id).execute()
        st.success("Eliminado")
    except Exception as e:
        st.error(f"Error eliminando: {e}")

def encuestas_post_capacitacion(usuario):
    """Visualización mejorada de Encuestas"""
    st.markdown("## 📋 Encuestas de Satisfacción")
    st.markdown("---")
    
    supabase = get_supabase_client()
    es_supervisor = usuario['rol'] in ('supervisor', 'sst', 'admin', 'gerente')

    # 1. Obtener capacitaciones finalizadas
    caps = supabase.table('capacitaciones').select(
        '*, asistentes_capacitacion!inner(*, usuarios!inner(*))'
    ).eq('estado', 'realizada').execute().data

    if not caps:
        st.info("ℹ️ No hay capacitaciones finalizadas para revisar.")
        return

    # --- DISEÑO DE DOS COLUMNAS (Filtros a la izquierda, Resultados a la derecha) ---
    col_filters, col_results = st.columns([1, 2], gap="large")
    
    # --- COLUMNA 1: FILTROS ---
    with col_filters:
        st.subheader("🔍 Filtros de Búsqueda")
        
        # Selector de Capacitación
        # Creamos un diccionario para el selectbox: {id: "Codigo - Tema"}
        opciones_caps = {c['id']: f"{c['codigo']} - {c['tema']}" for c in caps}
        cap_id = st.selectbox(
            "Seleccionar Capacitación",
            options=opciones_caps.keys(),
            format_func=lambda x: opciones_caps[x]
        )
        # Obtenemos el objeto de la capacitación seleccionada
        cap = next(c for c in caps if c['id'] == cap_id)

        # Selector de Trabajador
        trabajador_id = None
        nombre_trabajador = ""
        
        if es_supervisor:
            # Filtrar solo los que asistieron (asistio = true)
            asistentes = [a for a in cap['asistentes_capacitacion'] if a['asistio']]
            
            if not asistentes:
                st.warning("⚠️ Nadie asistió a esta capacitación.")
                return

            opciones_asist = {a['trabajador_id']: a['usuarios']['nombre_completo'] for a in asistentes}
            trabajador_id = st.selectbox(
                "Seleccionar Asistente",
                options=opciones_asist.keys(),
                format_func=lambda x: opciones_asist[x]
            )
            nombre_trabajador = opciones_asist[trabajador_id]
        else:
            # Si es trabajador normal, solo puede verse a sí mismo
            asistencia_propia = next(
                (a for a in cap['asistentes_capacitacion'] 
                 if a['trabajador_id'] == usuario['id'] and a['asistio']), 
                None
            )
            
            if not asistencia_propia:
                st.warning("⛔ No registras asistencia confirmada en esta capacitación.")
                return
            
            trabajador_id = usuario['id']
            nombre_trabajador = usuario['nombre_completo']

    # --- CONSULTA DE LA ENCUESTA ---
    enc_list = supabase.table('encuestas_capacitacion') \
        .select('*') \
        .eq('capacitacion_id', cap['id']) \
        .eq('trabajador_id', trabajador_id) \
        .execute().data
    
    enc = enc_list[0] if enc_list else None

    # --- COLUMNA 2: TARJETA DE RESULTADOS ---
    with col_results:
        st.subheader("📝 Detalle de Evaluación")
        
        if enc:
            # Diseño tipo "Tarjeta" con borde
            with st.container(border=True):
                # Encabezado de la tarjeta
                c_head1, c_head2 = st.columns([3, 1])
                with c_head1:
                    st.markdown(f"#### 👤 {nombre_trabajador}")
                    st.caption(f"Capacitación: {cap['tema']}")
                with c_head2:
                    st.success("✅ Completada")

                st.markdown("---")

                # Métricas visuales
                m1, m2 = st.columns(2)
                
                with m1:
                    score = int(enc['calificacion'])
                    stars = "⭐" * score + "☆" * (5 - score) # Ejemplo: ⭐⭐⭐⭐☆
                    st.metric("Calificación", f"{score}/5", delta=stars, delta_color="off")
                
                with m2:
                    # Formatear fecha
                    fecha_str = "Fecha desconocida"
                    if enc.get('fecha_respuesta'):
                        try:
                            fecha_str = pd.to_datetime(enc['fecha_respuesta']).strftime('%d/%m/%Y %H:%M')
                        except:
                            fecha_str = enc['fecha_respuesta']
                    st.metric("Enviado el", fecha_str)

                # Sección de Comentarios con estilo
                st.markdown("#### 💬 Comentarios y Sugerencias")
                if enc['comentarios'] and len(enc['comentarios']) > 2:
                    st.info(f"_{enc['comentarios']}_")
                else:
                    st.caption("No se dejaron comentarios adicionales.")

        else:
            # Diseño de Estado Pendiente
            with st.container(border=True):
                st.markdown(f"#### ⏳ Estado: Pendiente de Respuesta")
                st.markdown(f"El trabajador **{nombre_trabajador}** asistió a la capacitación, pero aún no tenemos su encuesta registrada.")
                
                col_warn, col_action = st.columns([2, 1])
                with col_warn:
                    st.warning("⚠️ Encuesta no encontrada en el sistema.")
                
                st.markdown("---")
                st.markdown("**Posibles causas:**")
                st.markdown("""
                - El trabajador no ha llenado el Google Form enviado a su correo.
                - Hubo un retraso en la sincronización (n8n).
                - El correo estaba mal escrito.
                """)

def guardar_encuesta(data):
    supabase = get_supabase_client()
    try:
        supabase.table('encuestas_capacitacion').insert(data).execute()
    except Exception as e:
        st.error(f"Error: {e}")

def reporte_efectividad(usuario):
    """Reporte visual de efectividad de capacitaciones (Dashboard)"""
    # Header con estilo
    st.markdown("## 📊 Reporte de Efectividad")
    st.markdown("---")
    
    supabase = get_supabase_client()

    # 1. Obtener datos crudos
    # Ordenamos por fecha descendente para ver lo más reciente primero
    realizadas = supabase.table('capacitaciones').select(
        '*, asistentes_capacitacion(*), encuestas_capacitacion(*)'
    ).eq('estado', 'realizada').order('fecha_programada', desc=True).execute().data

    if not realizadas:
        st.info("ℹ️ Aún no hay capacitaciones finalizadas para analizar.")
        return

    # 2. Procesar datos para KPIs y Tabla
    datos_tabla = []
    
    # Acumuladores para KPIs globales
    total_invitados_global = 0
    total_asistentes_global = 0
    suma_satisfaccion_global = 0
    count_cursos_con_encuesta = 0

    for cap in realizadas:
        # Calcular Asistencia
        # Invitados = total de registros en la tabla de unión (todos los convocados)
        invitados = len(cap['asistentes_capacitacion'])
        # Asistentes = los que tienen asistio = true
        asistentes = sum(1 for a in cap['asistentes_capacitacion'] if a['asistio'])
        
        tasa_asistencia = 0
        if invitados > 0:
            tasa_asistencia = asistentes / invitados # Decimal para barra de progreso (0.0 - 1.0)

        # Calcular Satisfacción
        encuestas = cap['encuestas_capacitacion']
        promedio_cap = 0
        if encuestas:
            promedio_cap = sum(e['calificacion'] for e in encuestas) / len(encuestas)
            suma_satisfaccion_global += promedio_cap
            count_cursos_con_encuesta += 1
        
        # Acumular globales
        total_invitados_global += invitados
        total_asistentes_global += asistentes

        datos_tabla.append({
            "Código": cap['codigo'],
            "Tema": cap['tema'],
            "Fecha": pd.to_datetime(cap['fecha_programada']).strftime('%d/%m/%Y'),
            "Invitados": invitados,
            "Asistentes": asistentes,
            "Tasa Asistencia": tasa_asistencia,
            "Encuestas": len(encuestas),
            "Satisfacción": promedio_cap
        })

    # 3. Mostrar KPIs (Indicadores Clave de Desempeño) con estilo
    # Usamos un contenedor para darle fondo o separación si se desea, por ahora columnas limpias
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    # Cálculos globales
    tasa_global_asist = (total_asistentes_global / total_invitados_global * 100) if total_invitados_global else 0
    satisfaccion_global = (suma_satisfaccion_global / count_cursos_con_encuesta) if count_cursos_con_encuesta else 0

    kpi1.metric("Total Capacitaciones", len(realizadas), border=True)
    kpi2.metric("Total Asistentes", total_asistentes_global, border=True)
    
    # Color delta según meta (ej: 80%)
    delta_asist = None
    if tasa_global_asist >= 80: delta_asist = "Meta cumplida"
    
    kpi3.metric("Tasa Asistencia Global", f"{tasa_global_asist:.1f}%", delta=delta_asist, border=True)
    
    kpi4.metric("Satisfacción Promedio", f"{satisfaccion_global:.1f} / 5.0", border=True)

    st.markdown("### 📈 Detalle por Capacitación")

    # 4. Mostrar Tabla Interactiva con Gráficos Integrados
    df = pd.DataFrame(datos_tabla)
    
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Código": st.column_config.TextColumn("Cód.", width="small"),
            "Tema": st.column_config.TextColumn("Tema", width="large"),
            "Fecha": st.column_config.TextColumn("Fecha", width="small"),
            "Tasa Asistencia": st.column_config.ProgressColumn(
                "Asistencia",
                help="Porcentaje de invitados que asistieron",
                format="%.1f%%",
                min_value=0,
                max_value=1,
            ),
            "Satisfacción": st.column_config.NumberColumn(
                "Calif. (1-5)",
                format="%.1f ⭐",
                help="Promedio de encuestas"
            ),
            "Invitados": st.column_config.NumberColumn("Inv.", help="Total convocados"),
            "Asistentes": st.column_config.NumberColumn("Asist.", help="Total presentes"),
            "Encuestas": st.column_config.NumberColumn("Enc.", help="Total encuestas respondidas"),
        },
        hide_index=True
    )

    # 5. Botón de descarga
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Reporte Completo (CSV)",
        data=csv,
        file_name=f"reporte_efectividad_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        type="primary"
    )