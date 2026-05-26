import streamlit as st
import pandas as pd
import os
from recomendador import cargar_dataset, recomendar, formatear_recomendaciones
from audio_search import AudioSearch
from letras import buscar_por_letra, formatear_resultados_letras

# ── Diseño ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Music AI Bot", page_icon="🎵", layout="centered")
st.markdown("""
    <style>
    .main .block-container { max-width: 750px; padding-top: 2rem; }
    div.stChatInput { position: fixed; bottom: 3rem; max-width: 750px; z-index: 99; }
    </style>
""", unsafe_allow_html=True)

# ── Cargar AudioSearch una sola vez ─────────────────────────────────────
CSV_PATH = "data/dataset_musica.csv"

@st.cache_resource
def cargar_audio_search():
    s = AudioSearch(CSV_PATH)
    s.build_index()
    return s

# ── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Módulos de IA")
    st.markdown("---")
    st.subheader("🎵 Buscar por Audio")

    st.markdown("**Subir un fragmento de audio**")
    archivo_audio = st.file_uploader(
        "(.flac / .wav / .mp3)",
        type=["flac", "wav", "mp3"],
        key="audio_uploader"
    )

    if archivo_audio is not None:
        if st.button("🔍 Buscar canción similar", key="btn_archivo"):
            with st.spinner("Analizando audio..."):
                searcher = cargar_audio_search()
                resultado = searcher.search_by_bytes(
                    archivo_audio.read(),
                    filename=archivo_audio.name,
                    top_n=5
                )
            if resultado.empty:
                st.warning("No se encontraron canciones similares.")
            else:
                st.success("¡Encontré estas canciones similares!")
                st.dataframe(resultado, use_container_width=True)
                top1 = resultado.iloc[0]
                msg = (f"🎵 Busqué por audio y la canción más similar es "
                       f"**{top1['Título']}** de **{top1['Artista']}** "
                       f"(similitud: {top1['Similitud']})")
                st.session_state.messages.append({"role": "assistant", "content": msg})

    st.markdown("---")

    st.markdown("**Grabar con micrófono**")
    audio_grabado = st.audio_input("🎙️ Graba un fragmento", key="mic_input")

    if audio_grabado is not None:
        if st.button("🔍 Buscar por grabación", key="btn_mic"):
            with st.spinner("Analizando grabación..."):
                searcher = cargar_audio_search()
                resultado = searcher.search_by_bytes(
                    audio_grabado.read(),
                    filename="grabacion.wav",
                    top_n=5
                )
            if resultado.empty:
                st.warning("No se encontraron canciones similares.")
            else:
                st.success("¡Encontré estas canciones similares!")
                st.dataframe(resultado, use_container_width=True)
                top1 = resultado.iloc[0]
                msg = (f"🎵 Busqué por grabación y la canción más similar es "
                       f"**{top1['Título']}** de **{top1['Artista']}** "
                       f"(similitud: {top1['Similitud']})")
                st.session_state.messages.append({"role": "assistant", "content": msg})

# ── Chat principal ───────────────────────────────────────────────────────
st.title("Music AI")
st.caption("Chatbot inteligente con corrección de búsqueda.")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! ¿Qué artista buscamos hoy?"}]
if "pending_artist" not in st.session_state:
    st.session_state.pending_artist = None

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Escribe un artista..."):
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        mensaje_espera = st.empty()

        if os.path.exists(CSV_PATH):
            df = cargar_dataset(CSV_PATH)

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
# Usar "streamlit run app.py" en la terminal para iniciar la aplicación.
