import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
from datetime import datetime

# -------------------------
# CONFIGURACIÓN GENERAL
# -------------------------
st.set_page_config(
    page_title="Dashboard de Conectividad",
    layout="wide"
)

DATA_FOLDER = "data"
RAW_FOLDER = "raw_data"

# -------------------------
# FUNCIONES
# -------------------------

@st.cache_data
def cargar_datos():
    registros = []

    if not os.path.exists(DATA_FOLDER):
        return pd.DataFrame()

    for file in os.listdir(DATA_FOLDER):

        if not file.endswith((".xlsx", ".csv")):
            continue

        nombre_sin_extension = os.path.splitext(file)[0]

        # Buscar fecha en cualquier parte del nombre
        match = re.search(r"\d{4}-\d{2}-\d{2}", nombre_sin_extension)
        if not match:
            continue

        fecha = datetime.strptime(match.group(), "%Y-%m-%d")

        file_path = os.path.join(DATA_FOLDER, file)

        try:
            if file.endswith(".csv"):
                df = pd.read_csv(file_path, sep=None, engine="python")
            else:
                df = pd.read_excel(file_path)
        except:
            continue

        df.columns = df.columns.str.lower().str.strip()

        required_cols = {"accesspoint", "macs"}
        if not required_cols.issubset(df.columns):
            continue

        for _, row in df.iterrows():

            if pd.notna(row["macs"]):
                macs = [
                    m.strip()
                    for m in str(row["macs"]).split(",")
                    if m.strip()
                ]
            else:
                macs = []

            registros.append({
                "fecha": fecha,
                "accesspoint": row["accesspoint"],
                "macs": macs
            })

    return pd.DataFrame(registros)


def calcular_metricas(df):
    macs_df = df.explode("macs")

    resumen_diario = (
        macs_df
        .groupby("fecha")
        .agg(
            macs_unicas=("macs", "nunique"),
            nodos_activos=("accesspoint", "nunique")
        )
        .reset_index()
    )

    return macs_df, resumen_diario


# -------------------------
# INTERFAZ
# -------------------------

st.title("📊 Dashboard Ejecutivo de Conectividad")

# 🔄 BOTÓN ACTUALIZAR DATOS
if st.button("🔄 Actualizar datos"):
    st.cache_data.clear()
    st.success("Datos actualizados correctamente ✅")
    st.rerun()

df_raw = cargar_datos()

if df_raw.empty:
    st.warning("No hay archivos válidos en la carpeta /data")
    st.stop()

macs_df, resumen_diario = calcular_metricas(df_raw)

# -------------------------
# FILTROS
# -------------------------

st.sidebar.header("📅 Filtros")

fechas_disponibles = sorted(df_raw["fecha"].unique())
fecha_seleccionada = st.sidebar.selectbox(
    "Selecciona una fecha",
    fechas_disponibles,
    index=len(fechas_disponibles) - 1
)

periodo = st.sidebar.radio(
    "Periodo de análisis",
    ["Día seleccionado", "Últimos 7 días", "Últimos 30 días"]
)

if periodo == "Día seleccionado":
    resumen_periodo = resumen_diario[
        resumen_diario["fecha"] == fecha_seleccionada
    ]
    macs_periodo = macs_df[
        macs_df["fecha"] == fecha_seleccionada
    ]
else:
    dias = 7 if "7" in periodo else 30
    fecha_inicio = fecha_seleccionada - pd.Timedelta(days=dias - 1)

    resumen_periodo = resumen_diario[
        resumen_diario["fecha"] >= fecha_inicio
    ]
    macs_periodo = macs_df[
        macs_df["fecha"] >= fecha_inicio
    ]

# -------------------------
# KPIs
# -------------------------

macs_unicas = int(macs_periodo["macs"].nunique())
nodos = int(macs_periodo["accesspoint"].nunique())

col1, col2 = st.columns(2)
col1.metric("📱 MACs únicas", f"{macs_unicas:,}")
col2.metric("🔌 Nodos activos", nodos)

# -------------------------
# GRÁFICA: MACs POR NODO
# -------------------------

macs_por_nodo = (
    macs_periodo
    .groupby("accesspoint")["macs"]
    .nunique()
    .reset_index()
    .sort_values(by="macs", ascending=False)
)

fig_bar = px.bar(
    macs_por_nodo,
    x="accesspoint",
    y="macs",
    title="MACs únicas por nodo",
    labels={"macs": "MACs únicas", "accesspoint": "Nodo"}
)

fig_bar.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_bar, use_container_width=True)

# -------------------------
# GRÁFICA: TENDENCIA DIARIA
# -------------------------

fig_line = px.line(
    resumen_periodo,
    x="fecha",
    y="macs_unicas",
    title="Tendencia diaria de MACs únicas",
    markers=True
)

st.plotly_chart(fig_line, use_container_width=True)

# -------------------------
# TABLA EJECUTIVA
# -------------------------

tabla = (
    macs_periodo
    .groupby("accesspoint")
    .agg(macs_unicas=("macs", "nunique"))
    .reset_index()
    .sort_values(by="macs_unicas", ascending=False)
)

st.subheader("📋 Resumen por nodo (MACs únicas)")
st.dataframe(tabla, use_container_width=True)

# -------------------------
# DESCARGA ARCHIVOS ORIGINALES
# -------------------------

st.subheader("📥 Descargar archivos originales")

if os.path.exists(RAW_FOLDER):

    raw_files = [
        f for f in os.listdir(RAW_FOLDER)
        if f.endswith((".xlsx", ".csv"))
    ]

    if raw_files:

        archivo_seleccionado = st.selectbox(
            "Selecciona un archivo",
            sorted(raw_files, reverse=True)
        )

        file_path = os.path.join(RAW_FOLDER, archivo_seleccionado)

        with open(file_path, "rb") as f:

            mime_type = (
                "text/csv"
                if archivo_seleccionado.endswith(".csv")
                else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.download_button(
                label="Descargar archivo",
                data=f,
                file_name=archivo_seleccionado,
                mime=mime_type
            )

    else:
        st.info("No hay archivos en la carpeta raw_data")

else:
    st.warning("La carpeta raw_data no existe")


