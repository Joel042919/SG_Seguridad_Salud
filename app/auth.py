import streamlit as st
from app.utils.supabase_client import get_supabase_client
from argon2 import PasswordHasher
ph = PasswordHasher()

def autenticar_usuario():
    """Sistema de autenticación simple con roles"""
    
    if 'usuario' not in st.session_state:
        st.session_state.usuario = None
    
    if st.session_state.usuario:
        return st.session_state.usuario
    
    st.title("🔐 Sistema SST Perú - Acceso")
    
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    
    if st.button("Iniciar Sesión"):
        supabase = get_supabase_client()
        
        # Hash simple (en producción usar bcrypt)
        #pwd_hash = ph.hash(password)
        #print(pwd_hash)
        
        try:
            response = supabase.table('usuarios')\
                .select('*')\
                .eq('email', email)\
                .execute()
            
            
            if response.data:
                usuario = response.data[0]
                password_encriptado = response.data[0]['password_hash']
                if ph.verify(password_encriptado, password):
                    st.session_state.usuario = usuario
                    st.success("✅ Acceso concedido")
                    st.rerun()  
                else:
                    st.error("❌ Credenciales inválidas")
            else:
                st.error("❌ Credenciales inválidas")
        except Exception as e:
            st.error(f"Error de autenticación: {e}")
    
    return None

def cerrar_sesion():
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

def requerir_rol(roles_permitidos):
    """Decorador para proteger módulos por rol"""
    if 'usuario' not in st.session_state:
        st.error("No autenticado")
        st.stop()
    
    if st.session_state.usuario['rol'] not in roles_permitidos:
        st.error(f"Acceso denegado. Rol requerido: {', '.join(roles_permitidos)}")
        st.stop()
