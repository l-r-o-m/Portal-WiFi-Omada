import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="WiFi Express", page_icon="📶")

# Conectar con Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("📶 Conéctate Ahora")
st.subheader("Obtén tu clave de WiFi por 30 días")

with st.form("formulario_pago"):
    nombre = st.text_input("Nombre y Apellido")
    whatsapp = st.text_input("Número de WhatsApp")
    edificio = st.selectbox("Edificio", ["Edificio Norte", "Torre Sur", "Departamentos Centro"])
    foto = st.file_uploader("Sube captura de tu transferencia", type=['jpg', 'jpeg', 'png'])
    
    boton_enviar = st.form_submit_button("VALIDAR Y OBTENER CLAVE")

if boton_enviar:
    if not nombre or not whatsapp or not foto:
        st.error("❌ Por favor, rellena todos los campos y sube el comprobante.")
    else:
        with st.spinner("Procesando..."):
            try:
                # 1. Leer la pestaña de Vouchers
                vouchers_df = conn.read(worksheet="Vouchers")
                
                # Filtrar los que dicen "Disponible" (ignorando mayúsculas/minúsculas)
                disponibles = vouchers_df[vouchers_df['Estado'].str.lower() == 'disponible']
                
                if disponibles.empty:
                    st.error("Lo sentimos, no hay vouchers disponibles en este momento. Contacta a soporte.")
                else:
                    # 2. Tomar el primer voucher disponible
                    indice_voucher = disponibles.index[0]
                    voucher_entregado = disponibles.at[indice_voucher, 'Codigo']
                    
                    # 3. Cambiar el estado a "Vendido"
                    vouchers_df.at[indice_voucher, 'Estado'] = 'Vendido'
                    conn.update(worksheet="Vouchers", data=vouchers_df)
                    
                    # 4. Registrar la venta en la pestaña "Registros"
                    registros_df = conn.read(worksheet="Registros")
                    nuevo_registro = pd.DataFrame([{
                        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Nombre": nombre,
                        "WhatsApp": whatsapp,
                        "Edificio": edificio,
                        "Voucher_Asignado": voucher_entregado,
                        "Nota": "Revisar comprobante"
                    }])
                    registros_actualizados = pd.concat([registros_df, nuevo_registro], ignore_index=True)
                    conn.update(worksheet="Registros", data=registros_actualizados)
                    
                    # 5. Mostrar el éxito
                    st.success("✅ ¡Pago registrado!")
                    st.markdown("### 🔑 TU CLAVE DE ACCESO:")
                    st.info(f"**{voucher_entregado}**")
                    st.caption("Importante: Valideramos tu captura en breve. Si el pago no procede, el voucher será desactivado.")
                    
            except Exception as e:
                st.error("Hubo un error al conectar con la base de datos. Intenta de nuevo.")