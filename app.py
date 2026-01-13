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

DATA_FOLDER = "data"  # carpeta donde se suben los Excel

# -------------------------
# FUNCIONES
# -------------------------
def cargar_datos():
    registros = []

    for file in os.listdir(DATA_FOLDER):
        if file.endswith(".xlsx"):
            try:
                fecha = datetime.strptime(file.replace(".xlsx", ""), "%Y-%m-%d")
            except:
                continue

            df = pd.read_excel(os.path.join(DATA_FOLDER, file))
            df.columns = df.columns.str.lower()

            for _, row in df.iterrows():
                macs = [m.strip() for m in str(row["macs"]).split(",")]

                registros.append({
                    "fecha": fecha,
                    "accesspoint": row["accesspoint"],
                    "usuarios_reportados": row["usuarios_unicos"],
                    "macs": macs
                })

    return pd.DataFrame(registros)


def calcular_metricas(df):
    # Explode MACs
    macs_df = df.explode("macs")

    # Métricas diarias
    resumen_diario = (
        macs_df
        .groupby("fecha")
        .agg(
            usuarios_reportados=("usuarios_reportados", "sum"),
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
    df_periodo = df_raw[df_raw["fecha"] == fecha_seleccionada]
    resumen_periodo = resumen_diario[resumen_diario["fecha"] == fecha_seleccionada]
else:
    dias = 7 if "7" in periodo else 30
    fecha_inicio = fecha_seleccionada - pd.Timedelta(days=dias)
    df_periodo = df_raw[df_raw["fecha"] >= fecha_inicio]
    resumen_periodo = resumen_diario[resumen_diario["fecha"] >= fecha_inicio]

# -------------------------
# KPIs
# -------------------------
usuarios = int(resumen_periodo["usuarios_reportados"].mean())
macs_unicas = int(resumen_periodo["macs_unicas"].mean())
nodos = int(resumen_periodo["nodos_activos"].mean())

col1, col2, col3 = st.columns(3)
col1.metric("👥 Usuarios promedio", f"{usuarios:,}")
col2.metric("📱 MACs únicas promedio", f"{macs_unicas:,}")
col3.metric("🔌 Nodos activos", nodos)

# -------------------------
# GRÁFICA: USUARIOS POR NODO
# -------------------------
usuarios_nodo = (
    df_periodo
    .groupby("accesspoint")["usuarios_reportados"]
    .mean()
    .reset_index()
    .sort_values(by="usuarios_reportados", ascending=False)
)

fig_bar = px.bar(
    usuarios_nodo,
    x="accesspoint",
    y="usuarios_reportados",
    title="Usuarios promedio por nodo",
    labels={"usuarios_reportados": "Usuarios", "accesspoint": "Nodo"}
)

st.plotly_chart(fig_bar, use_container_width=True)

# -------------------------
# GRÁFICA: TENDENCIA DIARIA
# -------------------------
fig_line = px.line(
    resumen_diario,
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
    df_periodo
    .groupby("accesspoint")
    .agg(
        usuarios_promedio=("usuarios_reportados", "mean"),
        macs_unicas=("macs", lambda x: len(set(sum(x, []))))
    )
    .reset_index()
    .sort_values(by="usuarios_promedio", ascending=False)
)

st.subheader("📋 Resumen por nodo")
st.dataframe(tabla, use_container_width=True)

