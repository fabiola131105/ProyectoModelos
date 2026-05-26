import pandas as pd
from rapidfuzz import fuzz
import requests
import os
import re

# BUSCAR EN INTERNET
def buscar_en_internet(frase):
    try:
        busqueda = " ".join(
    frase.split()[:5]
)

        url = (
            "https://api.lyrics.ovh/suggest/"
    + busqueda
        )
        response = requests.get(url)

        if response.status_code != 200:
            return None

        datos = response.json()

        if "data" not in datos:
            return None

        if len(datos["data"]) == 0:
            return None

        cancion = datos["data"][0]

        titulo = cancion["title"]
        artista = cancion["artist"]["name"]

        # Obtener letra completa
        url_letra = (
            f"https://api.lyrics.ovh/v1/"
            f"{artista}/{titulo}"
        )

        response_letra = requests.get(url_letra)

        if response_letra.status_code != 200:
            return None

        datos_letra = response_letra.json()

        letra = datos_letra.get(
            "lyrics",
            "Sin letra disponible"
        )

        return {
            "Titulo": titulo,
            "Artista": artista,
            "Album": "Desconocido",
            "Genero": "Desconocido",
            "Año": "Desconocido",
            "Letra": letra
        }

    except Exception:
        return None

# GUARDAR NUEVA CANCIÓN
def guardar_cancion_csv(
    nueva_cancion,
    ruta_csv="data/dataset_musica.csv"
):
    try:
        if os.path.exists(ruta_csv):

            df = pd.read_csv(ruta_csv)

        else:

            df = pd.DataFrame()

        nuevo_id = 1

        if not df.empty and "ID" in df.columns:

            nuevo_id = (
                int(df["ID"].max()) + 1
            )

        nueva_fila = {
            "ID": nuevo_id,
            "Titulo": nueva_cancion["Titulo"],
            "Artista": nueva_cancion["Artista"],
            "Album": nueva_cancion["Album"],
            "Genero": nueva_cancion["Genero"],
            "Año": nueva_cancion["Año"],
            "Letra": nueva_cancion["Letra"],
            "Audio_Path": ""
        }

        df = pd.concat([
            df,
            pd.DataFrame([nueva_fila])
        ], ignore_index=True)

        df.to_csv(
            ruta_csv,
            index=False,
            encoding="utf-8-sig"
        )

    except Exception as e:

        print(
            "Error guardando canción:",
            e
        )

# BUSCAR POR LETRA
def buscar_por_letra(
    frase,
    df_musica,
    top_n=5
):
    if "Letra" not in df_musica.columns:
        return pd.DataFrame()
    frase = re.sub(
    r"[^a-zA-Z0-9\s]",
    "",
    frase.lower()
)
    frase = frase.lower()

    resultados = []

    mejor_coincidencia = None

    mejor_score = 0

    # Reconocer canciones
    for _, row in df_musica.iterrows():

        letra = str(row["Letra"]).lower()

        # Comparar similitud
        similitud = fuzz.partial_ratio(
            frase,
            letra
        )

        # Guardar mejor coincidencia
        if similitud > mejor_score:

            mejor_score = similitud
            mejor_coincidencia = letra

        # SI HAY BUENA COINCIDENCIA
        if similitud >= 30:

            # Buscar fragmento encontrado
            palabras = frase.split()

            fragmento = letra[:120]

            for palabra in palabras:

                indice = letra.find(palabra)

                if indice != -1:

                    inicio = max(
                        0,
                        indice - 40
                    )

                    fin = min(
                        len(letra),
                        indice + 120
                    )

                    fragmento = letra[
                        inicio:fin
                    ]

                    break

            resultados.append({
                "Titulo": row["Titulo"],
                "Artista": row["Artista"],
                "Album": row["Album"],
                "Genero": row["Genero"],
                "Año": row["Año"],
                "Similitud": similitud,
                "Fragmento": fragmento
            })

    # CONVERTIR A DATAFRAME
    df_resultados = pd.DataFrame(resultados)

    # Ordenar por similitud
    if not df_resultados.empty:

        df_resultados = (
            df_resultados.sort_values(
                by="Similitud",
                ascending=False
            )
        )

        return df_resultados.head(top_n)

    # SI NO ENCUENTRA LOCALMENTE
    nueva_cancion = buscar_en_internet(
        frase
    )

    if nueva_cancion:

        guardar_cancion_csv(
            nueva_cancion
        )

        nuevo_resultado = pd.DataFrame([{
            "Titulo": nueva_cancion["Titulo"],
            "Artista": nueva_cancion["Artista"],
            "Album": nueva_cancion["Album"],
            "Genero": nueva_cancion["Genero"],
            "Año": nueva_cancion["Año"],
            "Similitud": 100,
            "Fragmento": nueva_cancion["Letra"][:120]
        }])

        return nuevo_resultado

    return pd.DataFrame()

# FORMATEAR RESULTADOS
def formatear_resultados_letras(
    df_rec,
    frase
):
    if df_rec.empty:

        return (
            f"No encontré canciones "
            f"relacionadas con '{frase}'."
        )

    respuesta = (
        f"🎵 Canciones relacionadas con:\n"
        f"'{frase}'\n\n"
    )

    # MOSTRAR RESULTADOS
    for i, row in df_rec.iterrows():

        respuesta += (
            f"{list(df_rec.index).index(i)+1}. "
            f"{row['Titulo']} — "
            f"{row['Artista']}\n"
        )

        respuesta += (
            f"Álbum: "
            f"{row['Album']}\n"
        )

        respuesta += (
            f"Género: "
            f"{row['Genero']}\n"
        )

        respuesta += (
            f"Año: "
            f"{str(row['Año'])[:4]}\n"
        )

        respuesta += (
            f"Coincidencia: "
            f"{row['Similitud']}%\n\n"
        )

        respuesta += (
            f"Fragmento encontrado:\n"
            f"\"{row['Fragmento']}\"\n\n"
        )

        respuesta += (
            "----------------------------------\n\n"
        )

    return respuesta
