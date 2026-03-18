import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Configuración de la Página
st.set_page_config(page_title="WiFi Express", page_icon="📶")

# --- CONFIGURACIÓN DE GOOGLE DRIVE ---
# Reemplaza esto con el ID de la carpeta que creaste en tu Drive
DRIVE_FOLDER_ID = "1hrKPWTZVvC-LZy2DmwEaxLaAwU30MtOb" 

# --- ESTILO PERSONALIZADO ---
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://raw.githubusercontent.com/l-r-o-m/Portal-WiFi-Omada/refs/heads/main/daniel-joshua-4rn8TAfLB4I-unsplash.jpg");
        background-size: cover;
        background-attachment: fixed;
    }
    .aviso-legal {
        background-color: rgba(0, 0, 0, 0.6);
        padding: 15px;
        border-left: 5px solid #ff4b4b;
        border-radius: 5px;
        margin-top: 50px;
        font-size: 14px;
        color: #f0f2f6;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Conectar con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN PARA SUBIR A DRIVE ---
def subir_imagen_drive(archivo):
    """Sube la imagen a una carpeta específica de Google Drive y devuelve la URL"""
    try:
        # Extraer credenciales directamente de los secrets de Streamlit
        creds_dict = st.secrets["connections"]["gsheets"]
        
        # Autorizar con el scope de Drive
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, 
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        
        # Construir el servicio de la API de Drive
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Preparar los metadatos y el archivo
        file_metadata = {
            'name': f"Comprobante_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name}",
            'parents': [DRIVE_FOLDER_ID]
        }
        
        media = MediaIoBaseUpload(
            io.BytesIO(archivo.getvalue()), 
            mimetype=archivo.type, 
            resumable=True
        )
        
        # Ejecutar subida
        file = drive_service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        
        # Opcional: Hacer que el archivo sea visible para quien tenga el enlace
        # (Ideal para que puedas darle clic desde tu Excel sin problemas de permisos)
        drive_service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        return file.get('webViewLink')
        
    except Exception as e:
        st.error(f"Error al comunicar con Google Drive: {e}")
        return "Error de subida"

# --- ENCABEZADO Y MENSAJE DE BIENVENIDA ---
st.title("📶 Conéctate Ahora")

st.markdown("""
### ¡Bienvenido!
Obtén acceso a la red WiFi ingresando los datos solicitados a continuación y adjuntando tu comprobante de pago por la cantidad de **$90 MXN**.
Disponibilidad de momento unicamente para edificio Los Reyes segundo piso, Casa Aldama ambos pisos.
Proximamente se instalara el WiFi para todos los pisos en Los Reyes.
""")
st.write("---")

# --- FORMULARIO ---
with st.form("formulario_pago", clear_on_submit=True):
    nombre = st.text_input("Nombre y Apellido")
    whatsapp = st.text_input("Número de WhatsApp")
    edificio = st.selectbox("Edificio", ["Edificio Norte", "Torre Sur", "Departamentos Centro"])
    foto = st.file_uploader("Sube captura de tu transferencia o foto de comprobante de depósito", type=['jpg', 'jpeg', 'png'])
    
    boton_enviar = st.form_submit_button("VALIDAR Y OBTENER CLAVE")

# --- LÓGICA DE PROCESAMIENTO ---
if boton_enviar:
    if not nombre or not whatsapp or not foto:
        st.error("❌ Por favor, rellena todos los campos y sube el comprobante.")
    else:
        with st.spinner("Procesando pago y asignando voucher..."):
            try:
                # 1. Leer Vouchers
                vouchers_df = conn.read(worksheet="Vouchers", ttl=0)
                disponibles = vouchers_df[vouchers_df['Estado'].astype(str).str.lower() == 'disponible']
                
                if disponibles.empty:
                    st.error("Lo sentimos, no hay vouchers disponibles. Contacta a soporte.")
                else:
                    # 2. Tomar voucher
                    indice_voucher = disponibles.index[0]
                    voucher_sucio = disponibles.at[indice_voucher, 'Codigo']
                    voucher_entregado = str(voucher_sucio).split('.')[0]
                    
                    # 3. Subir foto a Google Drive (NUEVO)
                    url_foto = subir_imagen_drive(foto)
                    
                    # 4. Actualizar estado
                    vouchers_df.at[indice_voucher, 'Estado'] = 'Vendido'
                    conn.update(worksheet="Vouchers", data=vouchers_df)
                    
                    # 5. Registrar venta
                    tz = pytz.timezone('America/Monterrey')
                    registros_df = conn.read(worksheet="Registros", ttl=0)
                    nuevo_registro = pd.DataFrame([{
                        "Fecha": datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S"),
                        "Nombre": nombre,
                        "WhatsApp": whatsapp,
                        "Edificio": edificio,
                        "Voucher_Asignado": voucher_entregado,
                        "Comprobante_URL": url_foto, # <--- Aquí se guarda el link de Drive
                        "Nota": "Pendiente de validar"
                    }])
                    
                    registros_actualizados = pd.concat([registros_df, nuevo_registro], ignore_index=True)
                    conn.update(worksheet="Registros", data=registros_actualizados)
                    
                    # 6. ÉXITO
                    st.balloons()
                    st.success("✅ ¡Registro completado con éxito!")
                    st.markdown(f"""
                    ### 🔑 TU CLAVE DE ACCESO:
                    ## **{voucher_entregado}**
                    ---
                    """)
                    st.info("Guarda tu clave. Tu comprobante pasará a revisión; si el pago no es validado, el acceso será revocado automáticamente.")
                    
            except Exception as e:
                st.error(f"Error crítico: {e}")

# --- TÉRMINOS Y CONDICIONES ---
st.markdown(
    """
    <div class="aviso-legal">
        <strong>Términos y Condiciones del Servicio:</strong><br>
        Cada clave de acceso tiene un costo de $90 MXN, está limitada a un solo dispositivo y cuenta con una vigencia exacta de 30 días (con expiración automática).
        <br><br>
        <strong>⚠️ Aviso Importante:</strong><br>
        Cualquier intento de fraude o falsificación de comprobantes de pago constituye un delito federal. Estas acciones resultarán en el bloqueo permanente del dispositivo implicado en nuestra red WiFi y se tomarán las medidas legales correspondientes.
    </div>
    """,
    unsafe_allow_html=True
)
