import pandas as pan
import numpy as np
import re
 
# ==========================
# CARGA DEL DATASET
# ==========================
 
def cargar_dataset(ruta):
    df_musica = pan.read_csv(ruta)
    df_musica["Genero"] = df_musica["Genero"].fillna("Desconocido")
    df_musica["Artista"] = df_musica["Artista"].fillna("Desconocido")
    df_musica["Titulo"] = df_musica["Titulo"].fillna("Sin titulo")
    return df_musica
 
# ==========================
# ONE HOT ENCODING DE GÉNEROS
# ==========================
 
def preparar_generos(df_musica):
    # Obtener una copia del dataframe original
    musicaConGeneros_df = df_musica.copy()
 
    # Para cada fila, iteramos sobre los géneros (pueden venir separados por / o &)
    for index, row in df_musica.iterrows():
        partes = re.split(r"[/&,]", str(row["Genero"]))
        for genero in partes:
            genero = genero.strip()
            if genero and genero.lower() != "desconocido":
                musicaConGeneros_df.at[index, genero] = 1
 
    # Llenar los valores nulos con 0 fuera de los bucles
    musicaConGeneros_df = musicaConGeneros_df.fillna(0)
    return musicaConGeneros_df
 
# ==========================
# OBTENER COLUMNAS DE GÉNEROS
# ==========================
 
def obtener_cols_genero(df_musica, musicaConGeneros_df):
    cols_base = list(df_musica.columns)
    cols_genero = [c for c in musicaConGeneros_df.columns if c not in cols_base]
    return cols_genero
 
# ==========================
# CONSTRUIR PERFIL DEL USUARIO
# ==========================
 
def construir_perfil(query, df_musica, musicaConGeneros_df, cols_genero):
    query_lower = query.lower()

    # CAMBIO: Usar .str.contains para buscar la palabra clave en el Artista o Género
    mask_artista = df_musica["Artista"].str.lower().str.contains(query_lower, na=False)
    mask_genero  = df_musica["Genero"].str.lower().str.contains(query_lower, na=False)

    entrada_usuario = df_musica[mask_artista | mask_genero].copy()
 
    # Asignar calificación simulada de 5.0 a todas las canciones encontradas
    entrada_usuario["rating"] = 5.0
 
    # Codificar las canciones del usuario con one hot encoding de géneros
    cancion_usuario = musicaConGeneros_df[musicaConGeneros_df["ID"].isin(entrada_usuario["ID"].tolist())]
    cancion_usuario = cancion_usuario.reset_index(drop=True)
 
    # Tabla solo con columnas de géneros
    tabla_generos = cancion_usuario[cols_genero].copy().astype(float)
 
    # Calcular el perfil del usuario — matriz de peso
    perfil_usuario = tabla_generos.transpose().dot(entrada_usuario["rating"].reset_index(drop=True))
 
    return perfil_usuario, entrada_usuario
 
# ==========================
# CALCULAR RECOMENDACIONES
# ==========================
 
def recomendar(query, df_musica, top_n=5):
    musicaConGeneros_df = preparar_generos(df_musica)
    cols_genero = obtener_cols_genero(df_musica, musicaConGeneros_df)
 
    perfil_usuario, entrada_usuario = construir_perfil(
        query, df_musica, musicaConGeneros_df, cols_genero
    )
 
    if perfil_usuario is None:
        # Fallback: búsqueda difusa en artista y género
        query_lower = query.lower()
        mask = (
            df_musica["Artista"].str.lower().str.contains(query_lower, na=False) |
            df_musica["Genero"].str.lower().str.contains(query_lower, na=False)
        )
        resultado = df_musica[mask].copy()
        resultado["puntuacion"] = 1.0
        return resultado[["ID", "Titulo", "Artista", "Album", "Genero", "Año", "puntuacion"]].head(top_n)
 
    # Tabla de géneros de todo el dataset
    generos_tabla = musicaConGeneros_df.set_index("ID")
    generos_tabla = generos_tabla[cols_genero].astype(float)
 
    # Realizar el promedio ponderado
    recom = pan.DataFrame(generos_tabla.index, columns=["ID"])
    recom["puntuacion"] = ((generos_tabla * perfil_usuario).sum(axis=1) / perfil_usuario.sum()).values
    recom = recom.sort_values(by="puntuacion", ascending=False)
 
    # Unir con el dataset original para obtener info de las canciones
    tabla_final = df_musica.join(recom.set_index("ID"), on="ID", how="right")
    tabla_final = tabla_final.sort_values(by="puntuacion", ascending=False)
    tabla_final = tabla_final[tabla_final["puntuacion"] > 0]
 
    return tabla_final[["ID", "Titulo", "Artista", "Album", "Genero", "Año", "puntuacion"]].head(top_n)
 
# ==========================
# FORMATEAR RESPUESTA
# ==========================
 
def formatear_recomendaciones(df_rec, query):
    if df_rec.empty:
        return "No encontre canciones para '" + query + "'. Intenta con otro artista o genero."
 
    respuesta = "Recomendaciones para '" + query + "':\n\n"
 
    for i, row in df_rec.iterrows():
        respuesta += str(list(df_rec.index).index(i) + 1) + ". " + row["Titulo"] + " — " + row["Artista"] + "\n"
        respuesta += "   Album: " + str(row["Album"]) + "  |  Genero: " + str(row["Genero"]) + "  |  Año: " + str(row["Año"])[:4] + "\n"
        respuesta += "   Puntuacion: " + str(round(row["puntuacion"], 4)) + "\n\n"
 
    return respuesta