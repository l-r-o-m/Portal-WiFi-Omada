import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import requests
import base64
import pytz  

IMGBB_API_KEY = "fbed3041e8525daf0adb14c7414b5335"

st.set_page_config(page_title="WiFi Express", page_icon="📶")
# --- ESTILO PERSONALIZADO ---
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://raw.githubusercontent.com/l-r-o-m/Portal-WiFi-Omada/refs/heads/main/daniel-joshua-4rn8TAfLB4I-unsplash.jpg");
        background-size: cover;
        background-attachment: fixed;
    }
    /* Estilo para que el texto se lea bien sobre el fondo */
    h1, h2, h3, p, span {
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Conectar con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def subir_imagen(archivo):
    """Sube la imagen a ImgBB y devuelve la URL"""
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": base64.b64encode(archivo.read()).decode('utf-8'),
    }
    res = requests.post(url, payload)
    if res.status_code == 200:
        return res.json()['data']['url']
    return "Error al subir foto"

st.title("📶 Conéctate Ahora")
st.subheader("Obtén tu clave de WiFi por 30 días")

with st.form("formulario_pago", clear_on_submit=True):
    nombre = st.text_input("Nombre y Apellido")
    whatsapp = st.text_input("Número de WhatsApp")
    edificio = st.selectbox("Edificio", ["Edificio Norte", "Torre Sur", "Departamentos Centro"])
    foto = st.file_uploader("Sube captura de tu transferencia", type=['jpg', 'jpeg', 'png'])
    
    boton_enviar = st.form_submit_button("VALIDAR Y OBTENER CLAVE")

if boton_enviar:
    if not nombre or not whatsapp or not foto:
        st.error("❌ Por favor, rellena todos los campos y sube el comprobante.")
    else:
        with st.spinner("Procesando pago y asignando voucher..."):
            try:
                # 1. Leer Vouchers (ttl=0 obliga a leer datos frescos del Excel)
                vouchers_df = conn.read(worksheet="Vouchers", ttl=0)
                
                # Filtrar disponibles
                disponibles = vouchers_df[vouchers_df['Estado'].astype(str).str.lower() == 'disponible']
                
                if disponibles.empty:
                    st.error("Lo sentimos, no hay vouchers disponibles. Contacta a soporte.")
                else:
                    # 2. Tomar el primer voucher y limpiar el .0
                    indice_voucher = disponibles.index[0]
                    voucher_sucio = disponibles.at[indice_voucher, 'Codigo']
                    voucher_entregado = str(voucher_sucio).split('.')[0] # Quita el .0 si existe
                    
                    # 3. Subir foto a la nube
                    url_foto = subir_imagen(foto)
                    
                    # 4. Actualizar estado en la pestaña Vouchers
                    vouchers_df.at[indice_voucher, 'Estado'] = 'Vendido'
                    conn.update(worksheet="Vouchers", data=vouchers_df)
                    
                    # 5. Registrar venta en pestaña Registros (Leyendo datos frescos)
                    tz = pytz.timezone('America/Monterrey')
                    registros_df = conn.read(worksheet="Registros", ttl=0)
                    nuevo_registro = pd.DataFrame([{
                        "Fecha": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
                        "Nombre": nombre,
                        "WhatsApp": whatsapp,
                        "Edificio": edificio,
                        "Voucher_Asignado": voucher_entregado,
                        "Comprobante_URL": url_foto,
                        "Nota": "Pendiente de validar"
                    }])
                    
                    # Concatenar y actualizar
                    registros_actualizados = pd.concat([registros_df, nuevo_registro], ignore_index=True)
                    conn.update(worksheet="Registros", data=registros_actualizados)
                    
                    # 6. ÉXITO
                    st.balloons()
                    st.success("✅ ¡Pago registrado con éxito!")
                    st.markdown(f"""
                    ### 🔑 TU CLAVE DE ACCESO:
                    ## **{voucher_entregado}**
                    ---
                    """)
                    st.info("Guarda tu clave. Si el pago no es validado, el acceso será revocado.")
                    
            except Exception as e:
                st.error(f"Error crítico: {e}")
