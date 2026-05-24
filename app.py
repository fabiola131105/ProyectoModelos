import streamlit as st
import pandas as pd
import os
#Diseño 
st.set_page_config(
    page_title="Music AI Bot",
    page_icon="🎵",
    layout="centered"
)

st.markdown("""
    <style>
    .main .block-container { max-width: 750px; padding-top: 2rem; }
    div.stChatInput { position: fixed; bottom: 3rem; max-width: 750px; z-index: 99; }
    </style>
""", unsafe_allow_html=True)

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
st.caption("Chatbot inteligente de recomendación, letras y reconocimiento musical.")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "¡Hola! Soy tu asistente musical. Puedes pedirme recomendaciones por género o artista, o escribir una frase de una canción para buscar su letra. ¿Qué escuchamos hoy?"}
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Pregúntale algo a tu asistente musical..."):

    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        mensaje_espera = st.empty()
        mensaje_espera.markdown("*Pensando...*")
        
        # Simulación de respuesta conectada al dataset
        respuesta_bot = f"Recibí tu petición: '{prompt}'. Aquí se llamará al modelo de Machine Learning correspondiente usando el archivo dataset_musica.csv."
        mensaje_espera.write(respuesta_bot)
        
    st.session_state.messages.append({"role": "assistant", "content": respuesta_bot})
    #Usar "streamlit run app.py" en la terminal para iniciar la aplicación.
