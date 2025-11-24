import streamlit as st
import sys
sys.path.append(".")

from app.auth import autenticar_usuario
from app.modules import (
    riesgos, inspecciones, capacitaciones, 
    incidentes, epp, documental, reportes, dashboard
)

with open("app/static/css/dashboard.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Configuración de página
st.set_page_config(
    page_title="Sistema SST Perú",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Autenticación
    usuario = autenticar_usuario()
    
    if not usuario:
        st.stop()
    
    # Sidebar - Navegación
    st.sidebar.title(f"👤 {usuario['nombre_completo']}")
    st.sidebar.markdown(f"**Rol:** {usuario['rol'].upper()}")
    
    modulo = st.sidebar.selectbox(
        "Módulos",
        [
            "🏠 Dashboard",
            "⚠️ Gestión de Riesgos",
            "📋 Inspecciones",
            "🎓 Capacitaciones",
            "🚨 Incidentes",
            "🛡️ Gestión de EPP",
            "📚 Documentos",
            "📊 Reportes"
        ]
    )
    
    # Router de módulos
    if modulo == "🏠 Dashboard":
        dashboard.mostrar(usuario)
    elif "Riesgos" in modulo:
        riesgos.mostrar(usuario)
    elif "Inspecciones" in modulo:
        inspecciones.mostrar(usuario)
    elif "Capacitaciones" in modulo:
        capacitaciones.mostrar(usuario)
    elif "Incidentes" in modulo:
        incidentes.mostrar(usuario)
    elif "EPP" in modulo:
        epp.mostrar(usuario)
    elif "Documentos" in modulo:
        documental.mostrar(usuario)
    elif "Reportes" in modulo:
        reportes.mostrar(usuario)
    

if __name__ == "__main__":
    main()
