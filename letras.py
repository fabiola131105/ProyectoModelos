import pandas as pd
from rapidfuzz import fuzz

# BUSCAR POR LETRA
def buscar_por_letra(
    frase,
    df_musica,
    top_n=5
):
    if "Letra" not in df_musica.columns:
        return pd.DataFrame()
    frase = frase.lower()
    resultados = []
    mejor_coincidencia = None
    mejor_score = 0

    # Reconoer canciones
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
        if similitud >= 60:
            # Buscar fragmento encontrado
            palabras = frase.split()
            fragmento = letra[:120]
            for palabra in palabras:
                indice = letra.find(palabra)
                if indice != -1:
                    inicio = max(0, indice - 40)
                    fin = min(len(letra), indice + 120)
                    fragmento = letra[inicio:fin]
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
        df_resultados = df_resultados.sort_values(
            by="Similitud",
            ascending=False
        )
    return df_resultados.head(top_n)

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
            f"{row['Titulo']} — {row['Artista']}\n"
        )
        respuesta += (
            f"Álbum: {row['Album']}\n"
        )
        respuesta += (
            f"Género: {row['Genero']}\n"
        )
        respuesta += (
            f"Año: {str(row['Año'])[:4]}\n"
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