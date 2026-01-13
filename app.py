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

            required_cols = {"accesspoint", "usuarios_unicos", "macs"}
            if not required_cols.issubset(df.columns):
                continue

            for _, row in df.iterrows():
                macs = [m.strip() for m in str(row["macs"]).split(",") if m.strip()]

                registros.append({
                    "fecha": fecha,
                    "accesspoint": row["accesspoint"],
                    "usuarios_reportados": row["usuarios_unicos"],
                    "macs": macs
                })

    return pd.DataFrame(registros)


def calcular_metricas(df):
    # Resumen diario SIN explode
    resumen_diario = (
        df
        .groupby("fecha")
        .agg(
            usuarios_reportados=("usuarios_reportados", "sum"),
            nodos_activos=("accesspoint", "nunique")
        )
        .reset_index()
    )

    # MACs únicas por día
    macs_df = df.explode("macs")

    macs_unicas = (
        macs_df
        .groupby("fecha")["macs"]
        .nunique()
        .reset_index(name="macs_unicas")
    )

    resumen_diario = resumen_diario.merge(macs_unicas, on="fecha")

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
    df_periodo = df_raw[df_raw["fecha"] == fecha_seleccionada]
else:
    dias = 7 if "7" in periodo else 30
    fecha_inicio = fecha_seleccionada - pd.Timedelta(days=dias)

    resumen_periodo = resumen_diario[resumen_diario["fecha"] >= fecha_inicio]
    df_periodo = df_raw[df_raw["fecha"] >= fecha_inicio]

# -------------------------
# KPIs (TOTALES)
# -------------------------
usuarios = int(resumen_periodo["usuarios_reportados"].sum())
macs_unicas = int(resumen_periodo["macs_unicas"].max())
nodos = int(resumen_periodo["nodos_activos"].max())

col1, col2, col3 = st.columns(3)
col1.metric("👥 Usuarios totales", f"{usuarios:,}")
col2.metric("📱 MACs únicas", f"{macs_unicas:,}")
col3.metric("🔌 Nodos activos", nodos)

# -------------------------
# GRÁFICA: USUARIOS POR NODO
# -------------------------
usuarios_nodo = (
    df_periodo
    .groupby("accesspoint")["usuarios_reportados"]
    .sum()
    .reset_index()
    .sort_values(by="usuarios_reportados", ascending=False)
)

fig_bar = px.bar(
    usuarios_nodo,
    x="accesspoint",
    y="usuarios_reportados",
    title="Usuarios totales por nodo",
    labels={"usuarios_reportados": "Usuarios", "accesspoint": "Nodo"}
)

fig_bar.update_layout(xaxis_tickangle=-45)

st.plotly_chart(fig_bar, use_container_width=True)

# -------------------------
# GRÁFICA: TENDENCIA DIARIA
# -------------------------
fig_line = px.line(
    resumen_periodo,
    x="fecha",
    y="usuarios_reportados",
    title="Tendencia diaria de usuarios",
    markers=True
)

st.plotly_chart(fig_line, use_container_width=True)

# -------------------------
# TABLA EJECUTIVA
# -------------------------
tabla = (
    macs_df[macs_df["fecha"].isin(df_periodo["fecha"])]
    .groupby("accesspoint")
    .agg(
        usuarios_totales=("usuarios_reportados", "sum"),
        macs_unicas=("macs", "nunique")
    )
    .reset_index()
    .sort_values(by="usuarios_totales", ascending=False)
)

st.subheader("📋 Resumen por nodo (totales)")
st.dataframe(tabla, use_container_width=True)

