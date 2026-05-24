import streamlit as st
import pandas as pd
import os
from recomendador import cargar_dataset, recomendar, formatear_recomendaciones

# Diseño 
st.set_page_config(page_title="Music AI Bot", page_icon="🎵", layout="centered")

# Estilos
st.markdown("""
    <style>
    .main .block-container { max-width: 750px; padding-top: 2rem; }
    div.stChatInput { position: fixed; bottom: 3rem; max-width: 750px; z-index: 99; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR RESTAURADO ---
with st.sidebar:
    st.title("Módulos de IA")
    st.write("Panel para interactuar con las funciones de audio.")
    st.markdown("---")
    st.subheader("Reconocimiento de Audio")
    
    archivo_audio = st.file_uploader(
        "Sube un fragmento de audio (.flac / .wav)", 
        type=["flac", "wav"]
    )
    
    if archivo_audio is not None:
        st.info("Audio recibido. Procesando frecuencias...")

st.title("Music AI")
st.caption("Chatbot inteligente con corrección de búsqueda.")

# Inicializar estados
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! ¿Qué artista buscamos hoy?"}]
if "pending_artist" not in st.session_state:
    st.session_state.pending_artist = None

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Lógica principal
if prompt := st.chat_input("Escribe un artista..."):
    
    # 1. Mostrar mensaje del usuario
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        mensaje_espera = st.empty()
        ruta_csv = "data/dataset_musica.csv"
        
        if os.path.exists(ruta_csv):
            df = cargar_dataset(ruta_csv)
            
            # --- LÓGICA DE CORRECCIÓN ---
            if st.session_state.pending_artist and prompt.lower() in ["si", "sí", "yes", "claro"]:
                df_rec = recomendar(st.session_state.pending_artist, df)
                respuesta_bot = formatear_recomendaciones(df_rec, st.session_state.pending_artist)
                st.session_state.pending_artist = None
            
            else:
                df_rec = recomendar(prompt.strip(), df)
                
                if df_rec.empty:
                    artistas_unicos = df["Artista"].unique()
                    sugerencia = None
                    for art in artistas_unicos:
                        if prompt[:3].lower() in art.lower():
                            sugerencia = art
                            break
                    
                    if sugerencia:
                        respuesta_bot = f"No encontré exactamente '{prompt}'. ¿Te refieres a **{sugerencia}**?"
                        st.session_state.pending_artist = sugerencia
                    else:
                        respuesta_bot = f"No encontré nada relacionado con '{prompt}'. Intenta con otro nombre."
                else:
                    respuesta_bot = formatear_recomendaciones(df_rec, prompt)
            
            mensaje_espera.markdown(respuesta_bot)
            st.session_state.messages.append({"role": "assistant", "content": respuesta_bot})
        else:
            st.error("Dataset no encontrado.")
    #Usar "streamlit run app.py" en la terminal para iniciar la aplicación.
