import streamlit as st
from supabase import create_client
import numpy as np
import pandas as pd
from datetime import datetime, date, time, timedelta
from fpdf import FPDF
import io
import re
from streamlit_calendar import calendar

def a_json(dato):
    if isinstance(dato, dict):
        return {k: a_json(v) for k, v in dato.items()}
    if isinstance(dato, (list, tuple)):
        return {a_json(v) for v in dato}
    if isinstance(dato, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(dato)
    if isinstance(dato, (np.floating, np.float64, np.float32)):
        return float(dato)
    if isinstance(dato, np.bool_):
        return bool(dato)
    if isinstance(dato, (pd.Timestamp, datetime, date)):
        return dato.isoformat()
    if isinstance(dato, time):
        return dato.strftime("%H:%M:%S")
    if pd.isna(dato):
        return None
    return dato
# ==================== CONEXIÓN SUPABASE ====================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Clinica Dental ORBAR", layout="wide", page_icon="🦷")

# ==================== CSS AZUL AGUA + VERDE CLARITO ====================
st.markdown("""
<style>
    /* FONDO AZUL MENTA FUERTE */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main .block-container, section.main > div {
        background-color: #00BFA6 !important;
    }
    
    /* SIDEBAR VERDE UN POCO MÁS FUERTE */
    [data-testid="stSidebar"] {
        background-color: #81C784 !important;
    }
    
    /* TODAS LAS LETRAS NEGRAS */
    *, h1, h2, h3, h4, h5, h6, p, label, span {
        color: #000000 !important;
    }
    
    /* INPUTS BLANCOS - AGARRA TODOS LOS TIPOS */
    input, textarea {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* NUMBER INPUT - EL DE EDAD QUE SIGUE NEGRO */
    [data-testid="stNumberInput"] input, 
    [data-testid="stNumberInput"] button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #00695C !important;
    }
    
    /* TEXT INPUT Y TEXT AREA */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #00695C !important;
        border-radius: 6px !important;
    }
    
    /* SELECTBOX - EL DROPDOWN NEGRO DEL SIDEBAR Y FORM */
    [data-testid="stSelectbox"] > div > div,
    [data-baseweb="select"] > div,
    div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* MENÚ DESPLEGABLE DEL SELECTBOX - ESTE ES EL CUADRO NEGRO */
    div[data-baseweb="popover"] ul,
    div[data-baseweb="menu"] {
        background-color: #FFFFFF !important;
    }
    div[data-baseweb="popover"] ul li,
    div[data-baseweb="menu"] li {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    div[data-baseweb="popover"] ul li:hover,
    div[data-baseweb="menu"] li:hover {
            background-color: #E0E0E0 !important;
            color: #000000 !important;
        }
</style>
""", unsafe_allow_html=True)

# ==================== FUNCIONES BASE DE DATOS ====================

def obtener_pacientes():
    return pd.DataFrame(supabase.table('pacientes').select("*").order('nombre').execute().data)

def insertar_paciente(nombre, edad, telefono, alergias, antecedentes):
    supabase.table('pacientes').insert({
        "nombre": nombre, "edad": edad, "telefono": telefono, 
        "alergias": alergias, "antecedentes": antecedentes
    }).execute()

def obtener_citas():
    return pd.DataFrame(supabase.table('citas').select("*, pacientes(nombre)").execute().data)

def insertar_cita(id_paciente, fecha, hora, dentista, motivo):
    try:
        datos = {
            "id_paciente": id_paciente,
            "fecha_cita": fecha,
            "hora_cita": hora,
            "dentista": dentista,
            "motivo": motivo
        }

        resultado = supabase.table("citas").insert(a_json(datos)).execute()

        if resultado.data:
            st.success("Cita agendada correctamente")
            return resultado.data[0]
        else:
            st.error("No se pudo agendar la cita.")
            st.json(resultado.model_dump())
            return None
    except Exception as e:
        st.error(f"Error al agendar cita: {e}")
        st.stop()

def actualizar_estatus_cita(id_cita, estatus):
    supabase.table('citas').update({"estatus": estatus}).eq('id', id_cita).execute()

def obtener_tratamientos():
    return pd.DataFrame(supabase.table('tratamientos').select("*").order('nombre').execute().data)

def insertar_tratamiento(nombre, precio, descripcion):
    supabase.table('tratamientos').insert({"nombre": nombre, "precio": precio, "descripcion": descripcion}).execute()

def insertar_pago(id_paciente, id_cita, concepto, monto):
    try:
        datos = {
            "id_paciente": id_paciente,
            "id_cita": id_cita,
            "concepto": concepto,
            "monto": monto,
            "fecha_pago": date.today()
        }
        resultado = supabase.table('pagos').insert(a_json(datos)).execute()

        if resultado.data:
            st.success("Pago registrado correctamente")
            return resultado.data[0]
        else:
            st.error("No se pudo registrar el pago")
            st.json(resultado.model_dump())
            return None
    except Exception as e:
        st.error(f"Error al registrar pago: {e}")
        st.stop()

def insertar_historial(id_cita, diagnostico, procedimiento, observaciones):
    try:
        datos = {
            "id_cita": id_cita, # ← Este es int64
            "diagnostico": diagnostico,
            "procedimiento": procedimiento,
            "observaciones": observaciones,
            "fecha": date.today()
        }
        # La magia está aquí ↓↓
        resultado = supabase.table('historial').insert(a_json(datos)).execute()

        if resultado.data:
            st.success("Historial guardado correctamente")
            return resultado.data[0]
        else:
            st.error("No se pudo guardar el historial")
            st.json(resultado.model_dump())
            return None
    except Exception as e:
        st.error(f"Error al guardar historial: {e}")
        st.stop()

def obtener_historial(id_paciente):
    citas = supabase.table('citas').select("id, fecha_cita, motivo").eq('id_paciente', id_paciente).execute().data
    ids_citas = [c['id'] for c in citas]
    if ids_citas:
        df_hist = pd.DataFrame(supabase.table('historial').select("*").in_('id_cita', ids_citas).execute().data)
        if not df_hist.empty:
            df_citas = pd.DataFrame(citas)
            df_hist = df_hist.merge(df_citas, left_on='id_cita', right_on='id', how='left')
            return df_hist.sort_values('fecha', ascending=False)
    return pd.DataFrame()

def guardar_diente(id_paciente, diente_num, estado):
    try:
        datos = {
            "id_paciente": id_paciente, # ← Este es int64
            "diente": diente_num, # ← Este también puede ser int64
            "estado": estado
        }
        # La magia está aquí ↓↓ usa a_json()
        resultado = supabase.table('odontograma').insert(a_json(datos)).execute()

        if resultado.data:
            st.success("Diente actualizado")
            return resultado.data[0]
        else:
            st.error("No se pudo actualizar el diente")
            st.json(resultado.model_dump())
            return None
    except Exception as e:
        st.error(f"Error al guardar diente: {e}")
        st.stop()

def obtener_odontograma(id_paciente):
    return pd.DataFrame(supabase.table('odontograma').select("*").eq('id_paciente', id_paciente).execute().data)

def insertar_receta(id_paciente, id_cita, medicamento, dosis, indicaciones):
    try:
        datos = {
            "id_paciente": id_paciente,
            "id_cita": id_cita,
            "medicamento": medicamento,
            "dosis": dosis,
            "indicaciones": indicaciones,
        }
        resultado = supabase.table('recetas').insert(a_json(datos)).execute()

        if resultado.data:
            st.success("Receta guardada correctamente")
            return resultado.data[0]
        else:
            st.error("No se pudo guardar la receta")
            st.json(resultado.model_dump())
            return None
    except Exception as e:
        st.error(f"Error al gaurdar receta: {e}")
        st.stop()

def generar_receta_pdf_varios(nombre_paciente, edad, lista_medicamentos, indicaciones):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Colores: Azul Aqua = (0, 191, 255), Verde Aqua = (0, 255, 191)
    
    # === 3 LÍNEAS AZUL AQUA LADO IZQUIERDO ===
    pdf.set_draw_color(0, 120, 215)
    pdf.set_line_width(0.8)
    pdf.line(8, 10, 8, 287)    # Línea 1
    pdf.line(11, 10, 11, 287)  # Línea 2
    pdf.line(14, 10, 14, 287)  # Línea 3
    
    # === ENCABEZADO ===
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 18)
    pdf.set_x(20)
    pdf.cell(0, 10, 'CLINICA ORBAR', 0, 1, 'C')
    
    pdf.set_font('Arial', '', 11)
    pdf.set_x(20)
    pdf.cell(0, 6, 'Dra. Zurisadai Orozco Barbina', 0, 1, 'C')
    pdf.set_x(20)
    pdf.cell(0, 6, 'Cedula Profesional: 13357690', 0, 1, 'C')
    pdf.set_x(20)
    pdf.cell(0, 6, 'Av. Libertad S/N, Magisterial, C.P 52500 Santa Cruz Atizapan', 0, 1, 'C')
    pdf.set_x(20)
    pdf.cell(0, 6, 'Tel: 729 107 3852', 0, 1, 'C')
    
    # === LÍNEA VERDE AQUA SEPARADORA ===
    pdf.ln(3)
    pdf.set_draw_color(0, 180, 120)
    pdf.set_line_width(1)
    pdf.line(20, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)
    
    # === TITULO RECETA ===
    pdf.set_font('Arial', 'B', 14)
    pdf.set_x(20)
    pdf.cell(0, 10, 'RECETA MEDICA', 0, 1, 'C')
    pdf.ln(3)
    
    # === DATOS PACIENTE ===
    pdf.set_font('Arial', 'B', 11)
    pdf.set_x(20)
    pdf.cell(0, 8, 'DATOS DEL PACIENTE', 0, 1, 'L')
    
    pdf.set_font('Arial', '', 11)
    pdf.set_x(20)
    pdf.cell(90, 7, f'Nombre: {nombre_paciente}', 0, 0)
    pdf.cell(90, 7, f'Edad: {edad} anos', 0, 1)
    pdf.set_x(20)
    pdf.cell(90, 7, f'Fecha: {datetime.now().strftime("%d/%m/%Y")}', 0, 0)
    pdf.cell(90, 7, f'Folio: {datetime.now().strftime("%Y%m%d%H%M")}', 0, 1)
    pdf.ln(6)
    
    # === TABLA MEDICAMENTOS ===
    pdf.set_font('Arial', 'B', 11)
    pdf.set_x(20)
    pdf.cell(0, 8, 'PRESCRIPCION:', 0, 1, 'L')
    
    # Encabezado tabla
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_x(20)
    pdf.cell(10, 8, '#', 1, 0, 'C', True)
    pdf.cell(90, 8, 'Medicamento', 1, 0, 'C', True)
    pdf.cell(80, 8, 'Dosis / Indicacion', 1, 1, 'C', True)
    
    # Filas de medicamentos
    pdf.set_font('Arial', '', 10)
    for i, item in enumerate(lista_medicamentos, 1):
        pdf.set_x(20)
        pdf.cell(10, 8, str(i), 1, 0, 'C')
        pdf.cell(90, 8, item['medicamento'], 1, 0)
        pdf.cell(80, 8, item['dosis'], 1, 1)
    
    pdf.ln(6)
    
    # === INDICACIONES ===
    pdf.set_font('Arial', 'B', 11)
    pdf.set_x(20)
    pdf.cell(0, 8, 'INDICACIONES GENERALES:', 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.set_x(20)
    pdf.multi_cell(180, 7, indicaciones, 0, 'J')
    
    # === FIRMA ===
    pdf.ln(15)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, '_____________________________', 0, 1, 'C')
    pdf.cell(0, 6, 'Dra. Zurisadai Orozco Barbina', 0, 1, 'C')
    pdf.cell(0, 6, 'Ced. Prof. 13357690', 0, 1, 'C')
    
    # Pie de página
    pdf.set_y(-25)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.set_x(20)
    pdf.cell(0, 5, 'Documento valido como receta medica. Evite la automedicacion.', 0, 1, 'C')
    
    return pdf

# ==================== CLASE PDF RECETA CHINGONA ====================
class RecetaPDF(FPDF):
    def header(self):
        # Fondo azul agua
        self.set_fill_color(224, 247, 250)
        self.rect(0, 0, 210, 297, 'F')
        
        # Encabezado
        self.set_font('Arial', 'B', 20)
        self.set_text_color(0, 96, 100)
        self.cell(0, 10, 'CLINICA DENTAL ORBAR', 0, 1, 'C')
        
        self.set_font('Arial', '', 11)
        self.cell(0, 6, 'Dra. Zurisadari Orozco Barbina- Cirujano Dentista', 0, 1, 'C')
        self.cell(0, 6, 'Cédula Profesional: 13357690 ', 0, 1, 'C')
        self.cell(0, 6, 'Av. Libertad S/N, Magisterial, 52500 Santa Cruz Atizapan', 0, 1, 'C')
        
        # Línea verde agua
        self.set_draw_color(38, 166, 154)
        self.set_line_width(1)
        self.line(10, 40, 200, 40)
        self.ln(15)
    
    def footer(self):
        self.set_y(-30)
        self.set_draw_color(38, 166, 154)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)
        self.set_font('Arial', 'I', 9)
        self.set_text_color(0, 96, 100)
        self.cell(0, 6, 'Esta receta es válida por 30 días a partir de su expedición', 0, 1, 'C')
        self.cell(0, 6, f'Expedida el {datetime.now().strftime("%d/%m/%Y")}', 0, 1, 'C')

def generar_receta_pdf(nombre_paciente, edad, medicamento, dosis, indicaciones):
    pdf = RecetaPDF()
    pdf.add_page()
    
    # Título RECETA
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 96, 100)
    pdf.cell(0, 10, 'R E C E T A M E D I C A', 0, 1, 'C')
    pdf.ln(8)
    
    # Datos paciente
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 8, f'Paciente: {nombre_paciente}', 0, 0)
    pdf.cell(95, 8, f'Edad: {edad} años', 0, 1)
    pdf.cell(95, 8, f'Fecha: {datetime.now().strftime("%d/%m/%Y")}', 0, 0)
    pdf.cell(95, 8, f'Folio: RX-{datetime.now().strftime("%Y%m%d%H%M")}', 0, 1)
    pdf.ln(10)
    
    # Símbolo Rx
    pdf.set_font('Arial', 'B', 24)
    pdf.set_text_color(38, 166, 154)
    pdf.cell(0, 10, 'Rx.', 0, 1)
    pdf.ln(3)
    
    # Medicamento
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 8, f'{medicamento}')
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(0, 7, f'Dosis: {dosis}')
    pdf.ln(3)
    pdf.multi_cell(0, 7, f'Indicaciones: {indicaciones}')
    pdf.ln(20)
    
    # Firma
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, '_____________________________________', 0, 1, 'C')
    pdf.cell(0, 6, 'Dra. Zurisadai  Orozco Barbina', 0, 1, 'C')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, 'Cédula Profesional: 13357690', 0, 1, 'C')
    
    return pdf

def generar_recibo_pdf(nombre_paciente, concepto, monto):
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_fill_color(224, 247, 250)
        pdf.rect(0, 0, 210, 297, 'F')
        pdf.set_font("Arial", "B", 18)
        pdf.set_text_color(0, 96, 100)
        pdf.cell(0, 12, "CONSULTORIO DENTAL ORBAR", ln=True, align="C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 8, "RECIBO DE PAGO", ln=True, align="C")
        pdf.ln(15)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"Paciente: {nombre_paciente}", ln=True)
        pdf.cell(0, 8, f"Concepto: {concepto}", ln=True)
        pdf.cell(0, 8, f"Monto: ${monto:,.2f} MXN", ln=True)
        pdf.cell(0, 8, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        pdf.cell(0, 8, f"Folio: RC-{datetime.now().strftime('%Y%m%d%H%M')}", ln=True)
        pdf.ln(25)
        pdf.set_text_color(0, 96, 100)
        pdf.cell(0, 10, "_______________________________", ln=True, align="C")
        pdf.cell(0, 10, "Firma y Sello", ln=True, align="C")
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Error al generar PDF: {e}")
        return None  # Importante: regresa None si falla

# ==================== MENÚ PRINCIPAL ====================
st.sidebar.title("🦷 Clinica Dental ORBAR")
menu = st.sidebar.selectbox("Módulo", ["Agenda", "Pacientes", "Tratamientos", "Pagos", "Historial Clínico", "Recetas"])

# -------------------- 1. AGENDA --------------------
if menu == "Agenda":
    st.header("Agenda de Citas")
    tab1, tab2, tab3 = st.tabs(["Calendario", "Agendar Cita", "Atender Cita"])
    
with tab1:
    st.subheader("📅 Calendario")
    
    # QUITAMOS EL DATE_INPUT - SOLO DEJAMOS FILTRO DE STATUS
    col1, col2 = st.columns([3,1])
    with col1:
        st.write("**Todas las citas registradas**")  # Título en lugar del date_input
    with col2:
        filtro_status = st.selectbox("Status", ["Todos", "Programada", "Confirmada", "Atendida", "Cancelada"], key="filtro_cal")

    # QUERY SIN FILTRO DE FECHA - TRAEMOS TODO
    query = supabase.table('citas').select('*, pacientes(nombre)')
    
    if filtro_status != "Todos":
        query = query.eq('estatus', filtro_status)
    
    # Ordenamos por fecha para que el calendario se vea bien
    query = query.order('fecha_cita', desc=False).order('hora_cita', desc=False)
    
    df_citas = pd.DataFrame(query.execute().data)

    if not df_citas.empty:
        events = []
        for _, row in df_citas.iterrows():
            # COLORES POR STATUS
            if row['estatus'] == 'Atendida':
                color = "#4CAF50"  # Verde
            elif row['estatus'] == 'Cancelada':
                color = "#F44336"  # Rojo
            elif row['estatus'] == 'Confirmada':
                color = "#2196F3"  # Azul
            else:  # Programada o Pendiente
                color = "#FF9800"  # Naranja
            
            nombre_pac = row['pacientes']['nombre'] if row['pacientes'] else 'Sin nombre'
            
            events.append({
                "id": row['id'],
                "title": f"{nombre_pac} - {row['motivo']}",
                "start": f"{row['fecha_cita']}T{row['hora_cita']}",
                "color": color
            })
        
        calendar(events=events, options={"initialView": "dayGridMonth", "locale": "es", "height": 600})
        
        # TABLA ABAJO CON TODAS LAS CITAS
        st.divider()
        st.subheader("Detalle de Citas")  # Cambiamos el título
        
        def colorear_status(estatus):
            colores = {
                'Programada': "background-color: #FFF3CD; color: #856404",
                'Confirmada': "background-color: #D4EDDA; color: #155724",
                'Atendida': "background-color: #D1ECF1; color: #0C5460",
                'Cancelada': "background-color: #F8D7DA; color: #721C24",
                'Pendiente': "background-color: #FFF3CD; color: #856404"
            }
            return colores.get(estatus, "")
        
        df_citas['paciente'] = df_citas['pacientes'].apply(lambda x: x['nombre'] if x else 'N/A')
        df_citas['fecha_hora'] = df_citas['fecha_cita'] + ' ' + df_citas['hora_cita']
        
        st.dataframe(
            df_citas[['fecha_hora', 'paciente', 'motivo', 'estatus']].style.map(colorear_status, subset=['estatus']),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No hay citas programadas")
    
    with tab2:
        st.subheader("➕ Agendar Nueva Cita")
        df_pacientes = obtener_pacientes()
        
        if df_pacientes.empty:
            st.warning("Primero registra un paciente en el módulo Pacientes")
        else:
            with st.form("form_cita", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    paciente_sel = st.selectbox("Paciente", df_pacientes['nombre'].tolist())
                    paciente_id = df_pacientes[df_pacientes['nombre']==paciente_sel]['id'].iloc[0]
                    fecha = st.date_input("Fecha", min_value=datetime.now().date())
                    dentista = st.selectbox("Dentista", ["Dra. Zurisadai Orozco Barbina"]) # ← AGREGADO
                with col2:
                    hora = st.time_input("Hora")
                    duracion = st.selectbox("Duración", [15, 30, 45, 60], index=1, format_func=lambda x: f"{x} min")
                
                motivo = st.text_area("Motivo de consulta", placeholder="Ej: Limpieza dental, Dolor de muela...")
                
                if st.form_submit_button("Agendar Cita"):
                    hora_fin = (datetime.combine(fecha, hora) + timedelta(minutes=duracion)).time()
                    citas_existentes = supabase.table('citas').select('*').eq('fecha_cita', str(fecha)).execute().data
                    
                    empalme = False
                    for cita in citas_existentes:
                        if cita['estatus'] not in ['Cancelada']:
                            hora_existente = datetime.strptime(cita['hora_cita'], '%H:%M:%S').time()
                            hora_fin_existente = (datetime.combine(fecha, hora_existente) + timedelta(minutes=cita.get('duracion', 30))).time()
                            if (hora < hora_fin_existente) and (hora_fin > hora_existente):
                                empalme = True
                                st.error(f"⚠️ Empalme con cita a las {hora_existente.strftime('%H:%M')}")
                                break
                    
                    if not empalme:
                        datos_cita = {
                            "id_paciente": paciente_id,
                            "fecha_cita": str(fecha),
                            "hora_cita": str(hora),
                            "dentista": dentista, # ← AGREGADO
                            "duracion": duracion,
                            "motivo": motivo,
                            "estatus": "Programada" # ← TU DEFAULT
                        }
                        supabase.table('citas').insert(a_json(datos_cita)).execute()
                        st.success("✅ Cita agendada correctamente")
                        
                        telefono = df_pacientes[df_pacientes['id']==paciente_id]['telefono'].iloc[0]
                        if telefono:
                            tel_limpio = re.sub(r'[^0-9]', '', telefono)
                            mensaje = f"Hola {paciente_sel}, tu cita en Clinica ORBAR quedo agendada para el {fecha.strftime('%d/%m/%Y')} a las {hora.strftime('%H:%M')}. Motivo: {motivo}."
                            link_wa = f"https://wa.me/52{tel_limpio}?text={mensaje.replace(' ', '%20')}"
                            st.link_button("📱 Enviar recordatorio por WhatsApp", link_wa)
                        st.rerun()
    
    with tab3:
        st.subheader("🩺 Atender Cita")

        # Seleccionar cita pendiente o confirmada
        citas_pendientes = supabase.table('citas').select('*, pacientes(nombre, edad, alergias)').in_('estatus', ['Programada', 'Confirmada']).order('fecha_cita, hora_cita').execute().data

        if citas_pendientes:
            opciones_citas = [f"{c['fecha_cita']} {c['hora_cita']} - {c['pacientes']['nombre']}" for c in citas_pendientes]
            cita_sel = st.selectbox("Selecciona cita a atender", opciones_citas)
            idx = opciones_citas.index(cita_sel)
            cita_data = citas_pendientes[idx]
            paciente_data = cita_data['pacientes']

            col1, col2, col3 = st.columns(3)
            col1.metric("Paciente", paciente_data['nombre'])
            col2.metric("Edad", f"{paciente_data['edad']} años")
            col3.metric("Motivo", cita_data['motivo'])

            st.divider()

            # HISTÓRICO DEL PACIENTE EN SIDEBAR
            with st.sidebar:
                st.subheader(f"📋 Histórico: {paciente_data['nombre']}")
                st.write(f"**Alergias:** {paciente_data['alergias'] if paciente_data['alergias'] else 'Ninguna'}")

                # Últimas 3 citas
                try:
                    hist_citas = supabase.table('citas').select('*').eq('id_paciente', cita_data['id_paciente']).eq('estatus', 'Atendida').limit(3).execute().data
                    # Ordenamos en Python por si Supabase no quiere
                    hist_citas = sorted(hist_citas, key=lambda x: x.get['fecha_cita',''], reverse=True)[:3]
                except Exception:
                    hist_citas = []
                if hist_citas:
                    st.write("**Últimas consultas:**")
                    for h in hist_citas:
                        st.caption(f"• {h['fecha_cita']} - {h['motivo']}")

            # FORMULARIO DE ATENCIÓN
            with st.form("form_atender"):
                diagnostico = st.text_area("Diagnóstico")
                tratamiento = st.text_area("Tratamiento realizado")
                observaciones = st.text_area("Observaciones / Notas")

                col1, col2 = st.columns(2)
                with col1:
                    nuevo_status = st.selectbox("Actualizar estatus", ["Atendida", "No se presento", "Reagendar"])
                with col2:
                    proxima_cita = st.date_input("Próxima cita sugerida", value=None)

                if st.form_submit_button("Guardar Atención", type="primary"):
                    # Actualizar cita
                    update_data = {
                        "estatus": nuevo_status,
                        "diagnostico": diagnostico,
                        "tratamiento": tratamiento,
                        "observaciones": observaciones
                    }
                    supabase.table('citas').update(a_json(update_data)).eq('id', cita_data['id']).execute()

                    st.success(f"✅ Cita marcada como {nuevo_status}")

                    # Si hay próxima cita, crearla
                    if proxima_cita and nuevo_status == "Atendida":
                        st.info(f"Recuerda agendar la próxima cita para {proxima_cita}")

                    st.rerun()
        else:
            st.info("No hay citas pendientes o confirmadas por atender")

# -------------------- 2. PACIENTES --------------------
elif menu == "Pacientes":
    st.header("Gestión de Pacientes")
    tab1, tab2 = st.tabs(["Lista de Pacientes", "Registrar Nuevo"])
    df_pacientes = obtener_pacientes()
    
    with tab1:
        busqueda = st.text_input("Buscar paciente")
        if busqueda and not df_pacientes.empty:
            df_pacientes = df_pacientes[df_pacientes['nombre'].str.contains(busqueda, case=False, na=False)]
        st.dataframe(df_pacientes, use_container_width=True, hide_index=True)
    
    with tab2:
        with st.form("form_paciente", clear_on_submit=True):
            nombre = st.text_input("Nombre completo*")
            col1, col2 = st.columns(2)
            with col1: edad = st.number_input("Edad", 1, 120, 18)
            with col2: telefono = st.text_input("Teléfono")
            alergias = st.text_area("Alergias")
            antecedentes = st.text_area("Antecedentes médicos")
            if st.form_submit_button("Guardar Paciente"):
                if nombre:
                    insertar_paciente(nombre, edad, telefono, alergias, antecedentes)
                    st.success("Paciente registrado correctamente")
                    st.rerun()
                else:
                    st.error("El nombre es obligatorio")

# ------------------- 3. TRATAMIENTOS -------------------
elif menu == "Tratamientos":
    st.header("Catálogo de Tratamientos")
    tab1, tab2 = st.tabs(["Lista", "Agregar Tratamiento"])
    df_trat = obtener_tratamientos()
    
    with tab1:
        st.subheader("Lista Editable")
        if df_trat.empty:
            st.info("No hay tratamientos. Agrégalos en la pestaña de al lado.")
        else:
            # TABLA EDITABLE
            df_editado = st.data_editor(
                df_trat,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "nombre": st.column_config.TextColumn("Nombre", required=True),
                    "precio": st.column_config.NumberColumn("Precio MXN", min_value=0, step=50, format="$ %d", required=True),
                    "descripcion": st.column_config.TextColumn("Descripción")
                },
                hide_index=True,
                use_container_width=True,
                num_rows="dynamic",
                key="editor_tratamientos"
            )
            
            # BOTÓN GUARDAR CAMBIOS
            if st.button("💾 Guardar Cambios", type="primary"):
                try:
                    # Actualizar cada fila existente
                    for idx, row in df_editado.iterrows():
                        if pd.notna(row['id']):  # Solo filas que ya existían
                            supabase.table('tratamientos').update({
                                'nombre': row['nombre'],
                                'precio': int(row['precio']),
                                'descripcion': row['descripcion'] if pd.notna(row['descripcion']) else ''
                            }).eq('id', row['id']).execute()
                    
                    # Insertar filas nuevas - las que no tienen ID
                    filas_nuevas = df_editado[df_editado['id'].isna()]
                    for idx, row in filas_nuevas.iterrows():
                        if pd.notna(row['nombre']) and pd.notna(row['precio']):
                            supabase.table('tratamientos').insert({
                                'nombre': row['nombre'],
                                'precio': int(row['precio']),
                                'descripcion': row['descripcion'] if pd.notna(row['descripcion']) else ''
                            }).execute()
                    
                    st.success("✅ Catálogo actualizado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
    
    with tab2:
        with st.form("form_trat", clear_on_submit=True):
            nombre = st.text_input("Nombre del tratamiento*")
            precio = st.number_input("Precio MXN*", min_value=0.0, step=50.0)
            desc = st.text_area("Descripción")
            if st.form_submit_button("Guardar Tratamiento"):
                if nombre and precio > 0:
                    insertar_tratamiento(nombre, precio, desc)
                    st.success("Tratamiento agregado")
                    st.rerun()
                else:
                    st.error("Nombre y precio son obligatorios")

# -------------------- 4. PAGOS --------------------
elif menu == "Pagos":
    st.header("Registrar Pago e Imprimir Recibo")
    df_pacientes = obtener_pacientes()
    df_trat = obtener_tratamientos()

    if df_pacientes.empty or df_trat.empty:
        st.warning("Registra pacientes y tratamientos primero")
    else:
        # FORM SOLO PARA CAPTURAR DATOS
        with st.form("form_pago", clear_on_submit=True):
            paciente_sel = st.selectbox("Paciente*", df_pacientes['nombre'].tolist())
            id_paciente = df_pacientes[df_pacientes['nombre']==paciente_sel]['id'].values[0]
            
            tratamientos_sel = st.multiselect(
                "Tratamientos*", 
                df_trat['nombre'].tolist(),
                help="Selecciona uno o varios tratamientos"
            )
            
            monto = 0
            detalle_precios = []
            if tratamientos_sel:
                for t in tratamientos_sel:
                    precio = df_trat[df_trat['nombre']==t]['precio'].values[0]
                    monto += precio
                    detalle_precios.append(f"{t}: ${precio:,.0f}")
                
                st.write("**Detalle:**")
                for d in detalle_precios:
                    st.caption(f"• {d}")
            
            st.metric("Monto a Pagar", f"${monto:,.2f} MXN")
            
            # ESTE BOTÓN SOLO GUARDA EN BD Y GUARDA PDF EN SESSION_STATE
            submitted = st.form_submit_button("Registrar Pago y Generar Recibo")
            
            if submitted:
                if tratamientos_sel and monto > 0:
                    tratamientos_str = ', '.join(tratamientos_sel)
                    insertar_pago(id_paciente, None, tratamientos_str, monto)
                    st.success("Pago registrado correctamente")
                    
                    # GENERAR PDF Y GUARDARLO EN SESSION_STATE
                    try:
                        pdf = generar_recibo_pdf(paciente_sel, tratamientos_str, monto)
                        if pdf:
                            st.session_state['pdf_recibo'] = pdf
                            st.session_state['nombre_recibo'] = f"Recibo_{paciente_sel}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                            st.session_state['mostrar_descarga'] = True
                        else:
                            st.warning("Pago guardado pero no se pudo generar el PDF")
                    except Exception as e:
                        st.error(f"Error al generar PDF: {e}")
                else:
                    st.error("Selecciona al menos un tratamiento")
        
        # FUERA DEL FORM: MOSTRAMOS EL BOTÓN DE DESCARGA SI EXISTE
        if st.session_state.get('mostrar_descarga', False):
            st.download_button(
                label="📄 Descargar Recibo PDF",
                data=st.session_state['pdf_recibo'],
                file_name=st.session_state['nombre_recibo'],
                mime="application/pdf"
            )
            # Limpiamos para que no se quede ahí siempre
            if st.button("Nuevo Pago"):
                st.session_state['mostrar_descarga'] = False
                st.rerun()

# -------------------- 5. HISTORIAL CLÍNICO + ODONTOGRAMA --------------------
elif menu == "Historial Clínico":
    st.header("Historial Clínico y Odontograma")
    df_pacientes = obtener_pacientes()
    if df_pacientes.empty:
        st.warning("Registra pacientes primero")
    else:
        paciente_sel = st.selectbox("Selecciona Paciente", df_pacientes['nombre'].tolist())
        paciente_data = df_pacientes[df_pacientes['nombre']==paciente_sel].iloc[0]
        id_paciente = paciente_data['id']
        
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Edad", f"{int(paciente_data['edad'])} años")
        with col2: st.metric("Teléfono", paciente_data['telefono'])
        with col3: st.metric("Alergias", paciente_data['alergias'] if paciente_data['alergias'] else "Ninguna")
        
        tab1, tab2 = st.tabs(["Odontograma", "Historial de Consultas"])
        
        with tab1:
            st.subheader("Odontograma - Haz clic en 💾 para guardar cada diente")
            df_odonto = obtener_odontograma(id_paciente)
            estados_dientes = {row['diente']: row['estado'] for _, row in df_odonto.iterrows()}
            
            st.write("**Arcada Superior**")
            cols = st.columns(8)
            dientes_sup = [18,17,16,15,14,13,12,11,21,22,23,24,25,26,27,28]
            for i, diente_num in enumerate(dientes_sup):
                with cols[i%8]:
                    estado = st.selectbox(f"#{diente_num}", ["Sano", "Caries", "Extraido", "Corona", "Endodoncia"], 
                                          index=["Sano", "Caries", "Extraido", "Corona", "Endodoncia"].index(estados_dientes.get(diente_num, "Sano")),
                                          key=f"d{diente_num}", label_visibility="collapsed")
                    if st.button("💾", key=f"b{diente_num}", use_container_width=True):
                        guardar_diente(id_paciente, diente_num, estado)
                        st.rerun()
            
            st.divider()
            st.write("**Arcada Inferior**")
            cols = st.columns(8)
            dientes_inf = [48,47,46,45,44,43,42,41,31,32,33,34,35,36,37,38]
            for i, diente_num in enumerate(dientes_inf):
                with cols[i%8]:
                    estado = st.selectbox(f"#{diente_num}", ["Sano", "Caries", "Extraido", "Corona", "Endodoncia"], 
                                          index=["Sano", "Caries", "Extraido", "Corona", "Endodoncia"].index(estados_dientes.get(diente_num, "Sano")),
                                          key=f"d{diente_num}", label_visibility="collapsed")
                    if st.button("💾", key=f"b{diente_num}", use_container_width=True):
                        guardar_diente(id_paciente, diente_num, estado)
                        st.rerun()
        
        with tab2:
            st.subheader("Historial de Consultas")
            df_pacientes = obtener_pacientes()
            if df_pacientes.empty:
                st.info("No hay pacientes registrados.")
            else:
                paciente_sel_hist = st.selectbox("Paciente", df_pacientes['nombre'].tolist(), key="hist_paciente")
                id_paciente_hist = df_pacientes[df_pacientes['nombre']==paciente_sel_hist]['id'].values[0]
                
                # FORZAMOS RELOAD SIN CACHE
                citas_paciente = supabase.table('citas')\
                .select('*, tratamientos(nombre)')\
                .eq('id_paciente', int(id_paciente_hist))\
                .order('fecha_hora', desc=True)\
                .execute().data
                
                df_citas_pac = pd.DataFrame(citas_paciente)
                
                if df_citas_pac.empty:
                    st.info("Este paciente no tiene citas registradas.")
                else:
                    # Desanidamos el tratamiento para que se vea bien
                    if 'tratamientos' in df_citas_pac.columns:
                        df_citas_pac['tratamiento'] = df_citas_pac['tratamientos'].apply(
                            lambda x: x['nombre'] if isinstance(x, dict) else 'N/A'
                        )
                    
                    # Mostramos todas las columnas importantes
                    columnas_mostrar = ['fecha_hora', 'tratamiento', 'estatus', 'motivo', 'diagnostico']
                    columnas_mostrar = [col for col in columnas_mostrar if col in df_citas_pac.columns]
                    
                    st.dataframe(
                        df_citas_pac[columnas_mostrar], 
                        use_container_width=True,
                        hide_index=True
                    )
# -------------------- 6. RECETAS --------------------
elif menu == "Recetas":
    st.header("Generar Receta Médica")
    df_pacientes = obtener_pacientes()
    if df_pacientes.empty:
        st.warning("Registra pacientes primero")
    else:
    # Inicializar lista si no existe
        if 'medicamentos_receta' not in st.session_state:
            st.session_state.medicamentos_receta = []

        col1, col2 = st.columns(2)
        with col1:
            paciente_sel = st.selectbox("Paciente", df_pacientes['nombre'].tolist())
            paciente_data = df_pacientes[df_pacientes['nombre']==paciente_sel].iloc[0]
        with col2:
            st.metric("Edad", f"{int(paciente_data['edad'])} años")
            st.metric("Alergias", paciente_data['alergias'] if paciente_data['alergias'] else "Ninguna")
        
        st.divider()
        
        # 1. FORM PARA AGREGAR MEDICAMENTOS UNO POR UNO
        with st.form("form_agregar_med", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            with c1:
                med = st.text_input("Medicamento", placeholder="Ej: Amoxicilina 500mg")
            with c2:
                dosis = st.text_input("Dosis", placeholder="Ej: 1 capsula c/8hrs")
            
            if st.form_submit_button("➕ Agregar a la receta"):
                if med and dosis:
                    st.session_state.medicamentos_receta.append({"medicamento": med, "dosis": dosis})
                    st.rerun()
                else:
                    st.warning("Completa medicamento y dosis")

        # 2. MOSTRAR LISTA DE MEDICAMENTOS AGREGADOS
        if st.session_state.medicamentos_receta:
            st.write("**Medicamentos agregados:**")
            for i, item in enumerate(st.session_state.medicamentos_receta):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"{i+1}. {item['medicamento']}")
                c2.write(item['dosis'])
                if c3.button("🗑️", key=f"del_{i}"):
                    st.session_state.medicamentos_receta.pop(i)
                    st.rerun()
            
            st.divider()
            
            # 3. INDICACIONES Y GENERAR PDF FINAL
            indicaciones = st.text_area("Indicaciones generales", placeholder="Ej: Tomar después de alimentos por 7 días...")
            
            if st.button("📄 Generar y Guardar Receta PDF", type="primary"):
                if indicaciones.strip():
                    # Guardar todos en Supabase
                    for item in st.session_state.medicamentos_receta:
                        insertar_receta(paciente_data['id'], None, item['medicamento'], item['dosis'], indicaciones)
                    
                    # Generar PDF con todos
                    pdf = generar_receta_pdf_varios(
                        paciente_sel, 
                        int(paciente_data['edad']), 
                        st.session_state.medicamentos_receta, 
                        indicaciones
                    )
                    st.success("Receta guardada correctamente")
                    
                    output = pdf.output(dest='S')
                    pdf_bytes = output.encode('latin-1') if isinstance(output, str) else bytes(output)
                    nombre_archivo = re.sub(r'[^a-zA-Z0-9_]', '_', paciente_sel)
                    
                    st.download_button(
                        label="📥 Descargar Receta PDF",
                        data=pdf_bytes,
                        file_name=f"Receta_{nombre_archivo}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf"
                    )
                    
                    # Limpiar lista
                    st.session_state.medicamentos_receta = []
                else:
                    st.error("Las indicaciones son obligatorias")
        else:
            st.info("Agrega al menos un medicamento para generar la receta")