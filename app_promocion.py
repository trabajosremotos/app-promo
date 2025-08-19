import streamlit as st
import pandas as pd
import io

st.title("Gestor de Inscripciones: Mapeo editable, plantilla de mapeo y visualización de Nuevos Registros")

# Carga de archivos
sw11_file = st.sidebar.file_uploader("Archivo SW11 (.xlsx)", type=["xlsx"])
promo_file = st.sidebar.file_uploader("Promoción (.xlsx)", type=["xlsx"])

def obtener_sheets_xlsx(file):
    try:
        xls = pd.ExcelFile(file)
        return xls.sheet_names
    except Exception:
        return []

sw11_sheet = promo_sheet = None
sw11_sheets = obtener_sheets_xlsx(sw11_file) if sw11_file else []
promo_sheets = obtener_sheets_xlsx(promo_file) if promo_file else []

if sw11_sheets:
    sw11_sheet = st.sidebar.selectbox("Hoja BDUnidad en SW11:", sw11_sheets, index=sw11_sheets.index("bduNIDAD") if "bduNIDAD" in sw11_sheets else 0)
if promo_sheets:
    promo_sheet = st.sidebar.selectbox("Hoja Promoción:", promo_sheets, index=promo_sheets.index("Tecnico") if "Tecnico" in promo_sheets else 0)

header_sw11 = st.sidebar.number_input("Fila de encabezado en SW11 (0-indexada)", 0, 10, 0)
header_promo = st.sidebar.number_input("Fila de encabezado en Promoción (0-indexada)", 0, 10, 1)

# ========================== PLANTILLA DE MAPEO =============================
st.sidebar.header("Plantilla de mapeo")

mapeo_file = st.sidebar.file_uploader("Cargar plantilla de mapeo (.xlsx)", type=["xlsx"])

# ============= PROCESAMIENTO DE ARCHIVOS Y MAPEOS =============

if sw11_file and promo_file and sw11_sheet and promo_sheet:
    bdunidad = pd.read_excel(sw11_file, sheet_name=sw11_sheet, header=header_sw11)
    promocion = pd.read_excel(promo_file, sheet_name=promo_sheet, header=header_promo)
    
    st.subheader(f"Vista previa BDUnidad ({sw11_sheet})")
    st.dataframe(bdunidad.head())
    st.subheader(f"Vista previa Promoción ({promo_sheet})")
    st.dataframe(promocion.head())

    # Columnas clave
    col_bd = "Cédula"
    col_promo_default = "Número de Documento de Identidad"

    if col_bd not in bdunidad.columns:
        st.error(f"La columna '{col_bd}' no existe en la hoja {sw11_sheet} de SW11.")
    elif col_promo_default not in promocion.columns:
        st.error(f"La columna '{col_promo_default}' no existe en la hoja {promo_sheet} de Promoción.")
    else:
        # Encontrar nuevos registros
        ids_bd = bdunidad[col_bd].astype(str).str.strip().str.lower().unique()
        ids_promo = promocion[col_promo_default].astype(str).str.strip().str.lower()
        nuevos_idx = ~ids_promo.isin(ids_bd)
        nuevos = promocion[nuevos_idx]
        repetidos = promocion[~nuevos_idx]

        st.subheader("🟢 Previsualización de registros NUEVOS (NO están en BDUnidad)")
        st.write(f"Total nuevos: {len(nuevos)}")
        st.dataframe(nuevos)

        if st.checkbox("Mostrar registros REPETIDOS (ya existen en BDUnidad)"):
            st.write(f"Total repetidos: {len(repetidos)}")
            st.dataframe(repetidos)

        # --- MAPEO EDITABLE o DESDE PLANTILLA ---
        st.subheader("🟠 Mapeo manual de columnas BDUnidad → Promoción")
        mapeo = {}
        sugeridos = {
            "Cédula": "Número de Documento de Identidad",
            "Primer nombre": "Nombre",
            "Mail": "Correo",
            "Teléfono": "Número de teléfono",
            "Nombre programa": "Programa",
            "Estado": "Estados",
            "Cohorte": "Periodo Académico"
        }
        # Si el usuario carga una plantilla de mapeo...
        mapeo_plantilla = None
        if mapeo_file is not None:
            try:
                mapeo_plantilla = pd.read_excel(mapeo_file)
                st.success("¡Plantilla de mapeo cargada!")
            except Exception as e:
                st.warning("No se pudo cargar la plantilla de mapeo. Elige otra o crea una nueva.")

        for col in bdunidad.columns:
            if mapeo_plantilla is not None and col in mapeo_plantilla["BDUnidad"].values:
                predef = mapeo_plantilla[mapeo_plantilla["BDUnidad"] == col]["Promocion"].values[0]
                predef = predef if predef in nuevos.columns else "(Dejar en blanco)"
            else:
                predef = sugeridos[col] if col in sugeridos and sugeridos[col] in nuevos.columns else "(Dejar en blanco)"
            mapeo[col] = st.selectbox(
                f"Columna para '{col}' (BDUnidad)",
                options=["(Dejar en blanco)"] + list(nuevos.columns),
                index=(["(Dejar en blanco)"] + list(nuevos.columns)).index(predef) if predef in nuevos.columns else 0,
                key=f"map_{col}"
            )

        # BOTÓN PARA DESCARGAR PLANTILLA DE MAPEO
        if st.button("Descargar este mapeo como plantilla (.xlsx)"):
            df_mapeo = pd.DataFrame({"BDUnidad": list(mapeo.keys()), "Promocion": list(mapeo.values())})
            output_map = io.BytesIO()
            df_mapeo.to_excel(output_map, index=False)
            st.download_button(
                label="Descargar plantilla de mapeo",
                data=output_map.getvalue(),
                file_name="plantilla_mapeo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # --- Previsualización de nuevos registros mapeados ---
        if len(nuevos) > 0:
            nuevos_mapeados = pd.DataFrame()
            for col in bdunidad.columns:
                col_promo = mapeo[col]
                if col_promo == "(Dejar en blanco)":
                    nuevos_mapeados[col] = ""
                else:
                    nuevos_mapeados[col] = nuevos[col_promo].astype(str)
            st.subheader("🟢 Previsualización de registros NUEVOS mapeados (listos para agregar)")
            st.dataframe(nuevos_mapeados)
            
            if st.button("Descargar nuevos registros mapeados (.xlsx)"):
                output = io.BytesIO()
                nuevos_mapeados.to_excel(output, index=False)
                st.download_button(
                    label="Descargar nuevos mapeados",
                    data=output.getvalue(),
                    file_name="nuevos_mapeados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
else:
    st.info("Por favor, sube ambos archivos, selecciona las hojas y el encabezado para cada uno.")

st.markdown("""
---
**Tips:**
- El mapeo lo puedes guardar y reutilizar.
- Si cambias columnas en tus archivos, puedes ajustar el mapeo antes de guardar/descargar.
- Solo se procesan los registros NUEVOS (no repetidos).
""")
