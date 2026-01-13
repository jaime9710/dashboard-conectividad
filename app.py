import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# -------------------------
# CONFIGURACIÓN GENERAL
# -------------------------
st.set_page_config(
    page_title="Dashboard de Conectividad",
    layout="wide"
)

DATA_FOLDER = "data"

# -------------------------
# FUNCIONES
# -------------------------
def cargar_datos():
    registros = []

    if not os.path.exists(DATA_FOLDER):
        return pd.DataFrame()

    for file in os.listdir(DATA_FOLDER):
        if file.endswith(".xlsx"):
            try:
                fecha = datetime.strptime(file.replace(".xlsx", ""), "%Y-%m-%d")
            except:
                continue

            df = pd.read_excel(os.path.join(DATA_FOLDER, file))
            df.columns = df.columns.str.lower()

            required_cols = {"accesspoint", "macs"}
            if not required_cols.issubset(df.columns):
                continue

            for _, row in df.iterrows():
                macs = [m.strip() for m in str(row["macs"]).split(",") if m.strip()]

                registros.append({
                    "fecha": fecha,
                    "accesspoint": row["accesspoint"],
                    "macs": macs
                })

    return pd.DataFrame(registros)


def calcular_metricas(df):
    # Explode de MACs
    macs_df = df.explode("macs")

    # Resumen diario SOLO MACs
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
# CARGA DE DATOS
# -------------------------
st.title("📊 Dashboard Ejecutivo de Conectividad")

df_raw = cargar_datos()

if df_raw.empty:
    st.warning("No hay archivos Excel válidos en la carpeta /data")
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
    resumen_periodo = resumen_diario[resumen_diario["fecha"] == fecha_seleccionada]
    macs_periodo = macs_df[macs_df["fecha"] == fecha_seleccionada]
else:
    dias = 7 if "7" in periodo else 30
    fecha_inicio = fecha_seleccionada - pd.Timedelta(days=dias)

    resumen_periodo = resumen_diario[resumen_diario["fecha"] >= fecha_inicio]
    macs_periodo = macs_df[macs_df["fecha"] >= fecha_inicio]

# -------------------------
# KPIs (SOLO MACs)
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
# GRÁFICA: TENDENCIA DIARIA DE MACs
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
    .agg(
        macs_unicas=("macs", "nunique")
    )
    .reset_index()
    .sort_values(by="macs_unicas", ascending=False)
)

st.subheader("📋 Resumen por nodo (MACs únicas)")
st.dataframe(tabla, use_container_width=True)
