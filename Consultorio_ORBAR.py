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
        return [a_json(v) for v in dato]
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

# ==================== FUNCION CALCULAR EDAD ====================
def calcular_edad(fecha_nacimiento):
    if fecha_nacimiento:
        hoy = date.today()
        return hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    return None

# ==================== CONEXIÓN SUPABASE ====================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Clinica Dental ORBAR", layout="wide", page_icon="🦷")

# ==================== CSS AZUL AGUA + VERDE CLARITO ====================
st.markdown("""
<style>
   .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"],.main.block-container, section.main > div {
        background-color: #00BFA6!important;
    }
    [data-testid="stSidebar"] {
        background-color: #81C784!important;
    }
    *, h1, h2, h3, h4, h5, h6, p, label, span {
        color: #000000!important;
    }
    input, textarea {
        background-color: #FFFFFF!important;
        color: #000000!important;
    }
    [data-testid="stNumberInput"] input,
    [data-testid="stNumberInput"] button {
        background-color: #FFFFFF!important;
        color: #000000!important;
        border: 2px solid #00695C!important;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        background-color: #FFFFFF!important;
        color: #000000!important;
        border: 2px solid #00695C!important;
        border-radius: 6px!important;
    }
    [data-testid="stDateInput"] input {
        background-color: #FFFFFF!important;
        color: #000000!important;
        border: 2px solid #00695C!important;
    }
    [data-testid="stSelectbox"] > div > div,
    [data-baseweb="select"] > div,
    div[data-baseweb="select"] {
        background-color: #FFFFFF!important;
        color: #000000!important;
    }
    div[data-baseweb="popover"] ul,
    div[data-baseweb="menu"] {
        background-color: #FFFFFF!important;
    }
    div[data-baseweb="popover"] ul li,
    div[data-baseweb="menu"] li {
        background-color: #FFFFFF!important;
        color: #000000!important;
    }
    div[data-baseweb="popover"] ul li:hover,
    div[data-baseweb="menu"] li:hover {
            background-color: #E0E0E0!important;
            color: #000000!important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== FUNCIONES BASE DE DATOS ====================

def obtener_pacientes():
    return pd.DataFrame(supabase.table('pacientes').select("*").order('nombre').execute().data)

# CAMBIO 3: Ahora usa fecha_nacimiento en lugar de edad
def insertar_paciente(nombre, fecha_nacimiento, telefono, alergias, antecedentes):
    supabase.table('pacientes').insert({
        "nombre": nombre,
        "fecha_nacimiento": fecha_nacimiento.isoformat() if fecha_nacimiento else None,
        "telefono": telefono,
        "alergias": alergias,
        "antecedentes": antecedentes
    }).execute()

# CAMBIO 2: Función para actualizar paciente
def actualizar_paciente(id_paciente, nombre, fecha_nacimiento, telefono, alergias, antecedentes):
    supabase.table('pacientes').update({
        "nombre": nombre,
        "fecha_nacimiento": fecha_nacimiento.isoformat() if fecha_nacimiento else None,
        "telefono": telefono,
        "alergias": alergias,
        "antecedentes": antecedentes
    }).eq('id', id_paciente).execute()

def obtener_citas():
    return pd.DataFrame(supabase.table('citas').select("*, pacientes(nombre)").execute().data)

# CAMBIO 1: Nueva función para obtener citas por fecha específica
def obtener_citas_por_fecha(fecha):
    return pd.DataFrame(supabase.table('citas').select("*, pacientes(nombre)").eq('fecha_cita', fecha.isoformat()).execute().data)

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
            "id_cita": id_cita,
            "diagnostico": diagnostico,
            "procedimiento": procedimiento,
            "observaciones": observaciones,
            "fecha": date.today()
        }
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
            "id_paciente": id_paciente,
            "diente": diente_num,
            "estado": estado
        }
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
    pdf.set_draw_color(0, 120, 215)
    pdf.set_line_width(0.8)
    pdf.line(8, 10, 8, 287)
    pdf.line(11, 10, 11, 287)
    pdf.line(14, 10, 14, 287)
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
    pdf.ln(3)
    pdf.set_draw_color(0, 180, 120)
    pdf.set_line_width(1)
    pdf.line(20, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_x(20)
    pdf.cell(0, 10, 'RECETA MEDICA', 0, 1, 'C')
    pdf.ln(3)
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
    pdf.set_font('Arial', 'B', 11)
    pdf.set_x(20)
    pdf.cell(0, 8, 'PRESCRIPCION:', 0, 1, 'L')
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_x(20)
    pdf.cell(10, 8, '#', 1, 0, 'C', True)
    pdf.cell(90, 8, 'Medicamento', 1, 0, 'C', True)
    pdf.cell(80, 8, 'Dosis / Indicacion', 1, 1, 'C', True)
    pdf.set_font('Arial', '', 10)
    for i, item in enumerate(lista_medicamentos, 1):
        pdf.set_x(20)
        pdf.cell(10, 8, str(i), 1, 0, 'C')
        pdf.cell(90, 8, item['medicamento'], 1, 0)
        pdf.cell(80, 8, item['dosis'], 1, 1)
    pdf.ln(6)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_x(20)
    pdf.cell(0, 8, 'INDICACIONES GENERALES:', 0, 1, 'L')
    pdf.set_font('Arial', '', 11)
    pdf.set_x(20)
    pdf.multi_cell(180, 7, indicaciones, 0, 'J')
    pdf.ln(15)
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, '_____________________________', 0, 1, 'C')
    pdf.cell(0, 6, 'Dra. Zurisadai Orozco Barbina', 0, 1, 'C')
    pdf.cell(0, 6, 'Ced. Prof. 13357690', 0, 1, 'C')
    pdf.set_y(-25)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.set_x(20)
    pdf.cell(0, 5, 'Documento valido como receta medica. Evite la automedicacion.', 0, 1, 'C')
    return pdf

class RecetaPDF(FPDF):
    def header(self):
        self.set_fill_color(224, 247, 250)
        self.rect(0, 0, 210, 297, 'F')
        self.set_font('Arial', 'B', 20)
        self.set_text_color(0, 96, 100)
        self.cell(0, 10, 'CLINICA DENTAL ORBAR', 0, 1, 'C')
        self.set_font('Arial', '', 11)
        self.cell(0, 6, 'Dra. Zurisadari Orozco Barbina- Cirujano Dentista', 0, 1, 'C')
        self.cell(0, 6, 'Cédula Profesional: 13357690 ', 0, 1, 'C')
        self.cell(0, 6, 'Av. Libertad S/N, Magisterial, 52500 Santa Cruz Atizapan', 0, 1, 'C')
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
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(0, 96, 100)
    pdf.cell(0, 10, 'R E C E T A M E D I C A', 0, 1, 'C')
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 8, f'Paciente: {nombre_paciente}', 0, 0)
    pdf.cell(95, 8, f'Edad: {edad} años', 0, 1)
    pdf.cell(95, 8, f'Fecha: {datetime.now().strftime("%d/%m/%Y")}', 0, 0)
    pdf.cell(95, 8, f'Folio: RX-{datetime.now().strftime("%Y%m%d%H%M")}', 0, 1)
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 24)
    pdf.set_text_color(38, 166, 154)
    pdf.cell(0, 10, 'Rx.', 0, 1)
    pdf.ln(3)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(0, 8, f'{medicamento}')
    pdf.ln(2)
    pdf.set_font('Arial', '', 12)
    pdf.multi_cell(0, 7, f'Dosis: {dosis}')
    pdf.ln(3)
    pdf.multi_cell(0, 7, f'Indicaciones: {indicaciones}')
    pdf.ln(20)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, '_____________________________________', 0, 1, 'C')
    pdf.cell(0, 6, 'Dra. Zurisadai Orozco Barbina', 0, 1, 'C')
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
        return None

def insertar_pago_completo(id_paciente, tratamientos, subtotal, descuento_tipo, descuento_valor, total, estatus, saldo_pendiente):
    data = {
        'id_paciente': int(id_paciente),
        'concepto': tratamientos, # Tu columna original
        'monto': total, # Tu columna original = total final
        'tratamientos': tratamientos,
        'subtotal': subtotal,
        'descuento_tipo': descuento_tipo,
        'descuento_valor': descuento_valor,
        'total': total,
        'estatus': estatus,
        'saldo_pendiente': saldo_pendiente
    }
    res = supabase.table('pagos').insert(data).execute()
    return res.data[0]['id'] if res.data else None

def insertar_abono(id_pago, monto_abono, metodo_pago):
    data = {
        'id_pago': int(id_pago),
        'monto_abono': monto_abono,
        'metodo_pago': metodo_pago
    }
    supabase.table('abonos').insert(data).execute()

def obtener_pagos_pendientes():
    res = supabase.table('pagos')\
      .select('*, pacientes(nombre)')\
      .eq('estatus', 'Pendiente')\
      .execute()
    return res.data

def actualizar_saldo_pago(id_pago, nuevo_estatus, nuevo_saldo):
    supabase.table('pagos')\
      .update({'estatus': nuevo_estatus, 'saldo_pendiente': nuevo_saldo})\
      .eq('id', int(id_pago))\
      .execute()

# ==================== MENÚ PRINCIPAL ====================
st.sidebar.title("🦷 Clinica Dental ORBAR")
menu = st.sidebar.selectbox("Módulo", ["Agenda", "Pacientes", "Tratamientos", "Pagos", "Historial Clínico", "Recetas"])

# -------------------- 1. AGENDA --------------------
if menu == "Agenda":
    st.header("Agenda de Citas")
    tab1, tab2, tab3 = st.tabs(["Calendario", "Agendar Cita", "Atender Cita"])
    with tab1:
        st.subheader("📅 Calendario")
        col1, col2 = st.columns([3,1])
        with col1:
            st.write("**Todas las citas registradas**")
        with col2:
            filtro_status = st.selectbox("Status", ["Todos", "Programada", "Confirmada", "Atendida", "Cancelada"], key="filtro_cal")

        query = supabase.table('citas').select('*, pacientes(nombre)')
        if filtro_status!= "Todos":
            query = query.eq('estatus', filtro_status)
        query = query.order('fecha_cita', desc=False).order('hora_cita', desc=False)
        df_citas = pd.DataFrame(query.execute().data)

        if not df_citas.empty:
            events = []
            for _, row in df_citas.iterrows():
                if row['estatus'] == 'Atendida':
                    color = "#4CAF50"
                elif row['estatus'] == 'Cancelada':
                    color = "#F44336"
                elif row['estatus'] == 'Confirmada':
                    color = "#2196F3"
                else:
                    color = "#FF9800"
                nombre_pac = row['pacientes']['nombre'] if row['pacientes'] else 'Sin nombre'
                events.append({
                    "id": row['id'],
                    "title": f"{nombre_pac} - {row['motivo']}",
                    "start": f"{row['fecha_cita']}T{row['hora_cita']}",
                    "color": color,
                    "extendedProps": {"fecha": row['fecha_cita']}
                })

            # CAMBIO 1: Capturamos el evento del click en el calendario
            calendario_resultado = calendar(
                events=events,
                options={"initialView": "dayGridMonth", "locale": "es", "height": 600},
                key="calendario_citas"
            )

            # CAMBIO 1: Si hacen clic en un día, mostramos modal con las citas
            if calendario_resultado and calendario_resultado.get('eventClick'):
                fecha_clickeada = calendario_resultado['eventClick']['event']['extendedProps']['fecha']
                citas_del_dia = obtener_citas_por_fecha(datetime.strptime(fecha_clickeada, '%Y-%m-%d').date())
                if not citas_del_dia.empty:
                    with st.expander(f"📋 Citas del {fecha_clickeada}", expanded=True):
                        for _, cita in citas_del_dia.iterrows():
                            nombre = cita['pacientes']['nombre'] if cita['pacientes'] else 'Sin nombre'
                            st.write(f"**{cita['hora_cita']}** - {nombre}")
                            st.write(f"Motivo: {cita['motivo']} | Dentista: {cita['dentista']} | Estatus: {cita['estatus']}")
                            st.divider()

            st.divider()
            st.subheader("Detalle de Citas")
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
                    dentista = st.selectbox("Dentista", ["Dra. Zurisadai Orozco Barbina"])
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
                            "dentista": dentista,
                            "duracion": duracion,
                            "motivo": motivo,
                            "estatus": "Programada"
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
        citas_pendientes = supabase.table('citas').select('*, pacientes(nombre, fecha_nacimiento, alergias)').in_('estatus', ['Programada', 'Confirmada']).order('fecha_cita').order('hora_cita').execute().data
        if citas_pendientes:
            opciones_citas = [f"{c['fecha_cita']} {c['hora_cita']} - {c['pacientes']['nombre']}" for c in citas_pendientes]
            cita_sel = st.selectbox("Selecciona cita a atender", opciones_citas)
            idx = opciones_citas.index(cita_sel)
            cita_data = citas_pendientes[idx]
            paciente_data = cita_data['pacientes']
            # CAMBIO 3: Calcular edad desde fecha_nacimiento
            edad_calc = calcular_edad(datetime.fromisoformat(paciente_data['fecha_nacimiento']).date()) if paciente_data.get('fecha_nacimiento') else "N/A"
            col1, col2, col3 = st.columns(3)
            col1.metric("Paciente", paciente_data['nombre'])
            col2.metric("Edad", f"{edad_calc} años" if edad_calc!= "N/A" else "N/A")
            col3.metric("Motivo", cita_data['motivo'])
            st.divider()
            with st.sidebar:
                st.subheader(f"📋 Histórico: {paciente_data['nombre']}")
                st.write(f"**Alergias:** {paciente_data['alergias'] if paciente_data['alergias'] else 'Ninguna'}")
                try:
                    hist_citas = supabase.table('citas').select('*').eq('id_paciente', cita_data['id_paciente']).eq('estatus', 'Atendida').limit(3).execute().data
                    hist_citas = sorted(hist_citas, key=lambda x: x.get('fecha_cita',''), reverse=True)[:3]
                except Exception:
                    hist_citas = []
                if hist_citas:
                    st.write("**Últimas consultas:**")
                    for h in hist_citas:
                        st.caption(f"• {h['fecha_cita']} - {h['motivo']}")
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
                    update_data = {
                        "estatus": nuevo_status,
                        "diagnostico": diagnostico,
                        "tratamiento": tratamiento,
                        "observaciones": observaciones
                    }
                    supabase.table('citas').update(a_json(update_data)).eq('id', cita_data['id']).execute()
                    st.success(f"✅ Cita marcada como {nuevo_status}")
                    if proxima_cita and nuevo_status == "Atendida":
                        st.info(f"Recuerda agendar la próxima cita para {proxima_cita}")
                    st.rerun()
        else:
            st.info("No hay citas pendientes o confirmadas por atender")

# -------------------- 2. PACIENTES --------------------
elif menu == "Pacientes":
    st.header("Gestión de Pacientes")
    tab1, tab2, tab3 = st.tabs(["Lista de Pacientes", "Registrar Nuevo", "Editar Paciente"])
    df_pacientes = obtener_pacientes()

    with tab1:
        busqueda = st.text_input("Buscar paciente")
        if busqueda and not df_pacientes.empty:
            df_pacientes_filtrado = df_pacientes[df_pacientes['nombre'].str.contains(busqueda, case=False, na=False)].copy()
        else:
            df_pacientes_filtrado = df_pacientes.copy()

        # CAMBIO 3: Calcular edad desde fecha_nacimiento con manejo de None
        if not df_pacientes_filtrado.empty and 'fecha_nacimiento' in df_pacientes_filtrado.columns:
            df_pacientes_filtrado['edad_calculada'] = df_pacientes_filtrado['fecha_nacimiento'].apply(
                lambda x: calcular_edad(pd.to_datetime(x).date()) if pd.notna(x) else None
            )

        st.dataframe(df_pacientes_filtrado, use_container_width=True, hide_index=True)

    with tab2:
        with st.form("form_paciente", clear_on_submit=True):
            nombre = st.text_input("Nombre completo*")
            col1, col2 = st.columns(2)
            with col1:
                # CAMBIO 3: Fecha de nacimiento en lugar de edad
                fecha_nac = st.date_input("Fecha de nacimiento*", max_value=date.today(), value=date(1950,1,1))
            with col2:
                telefono = st.text_input("Teléfono")
            alergias = st.text_area("Alergias")
            antecedentes = st.text_area("Antecedentes médicos")
            if st.form_submit_button("Guardar Paciente"):
                if nombre and fecha_nac:
                    insertar_paciente(nombre, fecha_nac, telefono, alergias, antecedentes)
                    st.success("Paciente registrado correctamente")
                    st.rerun()
                else:
                    st.error("El nombre y fecha de nacimiento son obligatorios")

    # CAMBIO 2: Pestaña para editar paciente
    with tab3:
        st.subheader("✏️ Editar Información de Paciente")
        if df_pacientes.empty:
            st.info("No hay pacientes registrados")
        else:
            paciente_editar = st.selectbox("Selecciona paciente a editar", df_pacientes['nombre'].tolist(), key="edit_paciente")
            paciente_data_edit = df_pacientes[df_pacientes['nombre']==paciente_editar].iloc[0]
            with st.form("form_editar_paciente"):
                nombre_edit = st.text_input("Nombre completo*", value=paciente_data_edit['nombre'])
                col1, col2 = st.columns(2)
                with col1:
                    fecha_nac_edit = st.date_input(
                        "Fecha de nacimiento*",
                        value=pd.to_datetime(paciente_data_edit['fecha_nacimiento']).date() if pd.notna(paciente_data_edit.get('fecha_nacimiento')) else date(1950,1,1),
                        max_value=date.today()
                    )
                with col2:
                    telefono_edit = st.text_input("Teléfono", value=paciente_data_edit['telefono'] if pd.notna(paciente_data_edit['telefono']) else "")
                alergias_edit = st.text_area("Alergias", value=paciente_data_edit['alergias'] if pd.notna(paciente_data_edit['alergias']) else "")
                antecedentes_edit = st.text_area("Antecedentes médicos", value=paciente_data_edit['antecedentes'] if pd.notna(paciente_data_edit['antecedentes']) else "")
                if st.form_submit_button("Actualizar Paciente", type="primary"):
                    if nombre_edit and fecha_nac_edit:
                        actualizar_paciente(paciente_data_edit['id'], nombre_edit, fecha_nac_edit, telefono_edit, alergias_edit, antecedentes_edit)
                        st.success("✅ Paciente actualizado correctamente")
                        st.rerun()
                    else:
                        st.error("El nombre y fecha de nacimiento son obligatorios")

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
                        if pd.notna(row['id']): # Solo filas que ya existían
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
    st.header("💳 Registrar Pago y Abonos")

    if 'mostrar_descarga' not in st.session_state:
        st.session_state['mostrar_descarga'] = False

    df_pacientes = obtener_pacientes()
    df_trat = obtener_tratamientos()

    if df_pacientes.empty or df_trat.empty:
        st.warning("Registra pacientes y tratamientos primero")
    else:
        tab1, tab2 = st.tabs(["💰 Nuevo Pago", "📝 Registrar Abono"])

        with tab1:
            with st.form("form_pago", clear_on_submit=True):
                paciente_sel = st.selectbox("Paciente*", df_pacientes['nombre'].tolist())
                id_paciente = df_pacientes[df_pacientes['nombre']==paciente_sel]['id'].values[0]

                tratamientos_sel = st.multiselect("Tratamientos*", df_trat['nombre'].tolist())

                subtotal = 0
                if tratamientos_sel:
                    for t in tratamientos_sel:
                        precio = df_trat[df_trat['nombre']==t]['precio'].values[0]
                        subtotal += precio
                        st.caption(f"• {t}: ${precio:,.0f}")

                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    descuento_tipo = st.selectbox("Descuento", ["Sin descuento", "Porcentaje %", "Monto fijo $"])
                with col2:
                    descuento_valor = st.number_input("Valor descuento", min_value=0.0, value=0.0, step=10.0)

                descuento_calc = 0
                if descuento_tipo == "Porcentaje %":
                    descuento_calc = subtotal * (descuento_valor / 100)
                elif descuento_tipo == "Monto fijo $":
                    descuento_calc = descuento_valor

                total = max(0, subtotal - descuento_calc)

                col1, col2, col3 = st.columns(3)
                col1.metric("Subtotal", f"${subtotal:,.2f}")
                col2.metric("Descuento", f"-${descuento_calc:,.2f}")
                col3.metric("TOTAL", f"${total:,.2f} MXN")

                tipo_pago = st.radio("Forma de pago", ["Pago completo", "Abono"], horizontal=True)

                monto_inicial = total
                metodo_pago = "Efectivo"
                if tipo_pago == "Abono":
                    col1, col2 = st.columns(2)
                    with col1:
                        monto_inicial = st.number_input("Abono inicial", min_value=0.01, max_value=float(total), step=50.0)
                    with col2:
                        metodo_pago = st.selectbox("Método", ["Efectivo", "Tarjeta", "Transferencia"])

                if st.form_submit_button("💾 Registrar Pago", type="primary"):
                    if tratamientos_sel and total > 0:
                        tratamientos_str = ', '.join(tratamientos_sel)
                        estatus = "Pagado" if tipo_pago == "Pago completo" or monto_inicial >= total else "Pendiente"
                        saldo_pendiente = 0 if estatus == "Pagado" else total - monto_inicial

                        id_pago = insertar_pago_completo(
                            id_paciente, tratamientos_str, subtotal,
                            descuento_tipo, descuento_valor, total,
                            estatus, saldo_pendiente
                        )

                        if monto_inicial > 0:
                            insertar_abono(id_pago, monto_inicial, metodo_pago)

                        st.success(f"Pago #{id_pago} registrado. {estatus}")
                        if estatus == "Pagado": st.balloons()
                        st.rerun()
                    else:
                        st.error("Selecciona al menos un tratamiento")

        with tab2:
            pagos_pendientes = obtener_pagos_pendientes()
            
            if not pagos_pendientes:
                st.info("No hay pagos pendientes")
            else:
                opciones = [f"#{p['id']} - {p['pacientes']['nombre']} - Debe: ${p['saldo_pendiente']:,.2f}" for p in pagos_pendientes]
                pago_sel_str = st.selectbox("Pago pendiente", opciones)
                id_pago_sel = int(pago_sel_str.split('#')[1].split(' ')[0])
                pago_data = next(p for p in pagos_pendientes if p['id'] == id_pago_sel)

                st.metric("Saldo pendiente", f"${pago_data['saldo_pendiente']:,.2f}")
                st.caption(f"Concepto: {pago_data['concepto']}")

                with st.form("form_abono"):
                    monto_abono = st.number_input("Monto del abono*", min_value=0.01, max_value=float(pago_data['saldo_pendiente']), step=50.0)
                    metodo = st.selectbox("Método", ["Efectivo", "Tarjeta", "Transferencia"])

                    if st.form_submit_button("Registrar Abono", type="primary"):
                        insertar_abono(id_pago_sel, monto_abono, metodo)
                        nuevo_saldo = pago_data['saldo_pendiente'] - monto_abono
                        nuevo_estatus = "Pagado" if nuevo_saldo <= 0 else "Pendiente"
                        actualizar_saldo_pago(id_pago_sel, nuevo_estatus, nuevo_saldo)
                        st.success(f"Abono registrado. Nuevo saldo: ${nuevo_saldo:,.2f}")
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

        # CAMBIO 3: Calcular edad desde fecha_nacimiento
        edad_calc = calcular_edad(datetime.fromisoformat(paciente_data['fecha_nacimiento']).date()) if paciente_data.get('fecha_nacimiento') else "N/A"

        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Edad", f"{edad_calc} años" if edad_calc!= "N/A" else "N/A")
        with col2: st.metric("Teléfono", paciente_data['telefono'] if pd.notna(paciente_data['telefono']) else "N/A")
        with col3: st.metric("Alergias", paciente_data['alergias'] if paciente_data['alergias'] else "Ninguna")

        tab1, tab2 = st.tabs(["Odontograma", "Historial de Consultas"])

        with tab1:
            st.subheader("Odontograma - Haz clic en 💾 para guardar cada diente")
            df_odonto = obtener_odontograma(id_paciente)
            estados_dientes = {row['diente']: row['estado'] for _, row in df_odonto.iterrows()}

            # CAMBIO 4: Odontograma con numeración FDI clara
            st.write("**Arcada Superior**")
            st.caption("Lado Derecho ← → Lado Izquierdo del paciente")
            cols = st.columns(8)
            dientes_sup = [18,17,16,15,14,13,12,11,21,22,23,24,25,26,27,28]
            for i, diente_num in enumerate(dientes_sup):
                with cols[i%8]:
                    st.caption(f"**#{diente_num}**") # CAMBIO 4: Mostrar número del diente
                    estado = st.selectbox(
                        f"Estado",
                        ["Sano", "Caries", "Extraido", "Corona", "Endodoncia"],
                        index=["Sano", "Caries", "Extraido", "Corona", "Endodoncia"].index(estados_dientes.get(diente_num, "Sano")),
                        key=f"d{diente_num}",
                        label_visibility="collapsed"
                    )
                    if st.button("💾", key=f"b{diente_num}", use_container_width=True):
                        guardar_diente(id_paciente, diente_num, estado)
                        st.rerun()

            st.divider()
            st.write("**Arcada Inferior**")
            st.caption("Lado Derecho ← → Lado Izquierdo del paciente")
            cols = st.columns(8)
            dientes_inf = [48,47,46,45,44,43,42,41,31,32,33,34,35,36,37,38]
            for i, diente_num in enumerate(dientes_inf):
                with cols[i%8]:
                    st.caption(f"**#{diente_num}**") # CAMBIO 4: Mostrar número del diente
                    estado = st.selectbox(
                        f"Estado",
                        ["Sano", "Caries", "Extraido", "Corona", "Endodoncia"],
                        index=["Sano", "Caries", "Extraido", "Corona", "Endodoncia"].index(estados_dientes.get(diente_num, "Sano")),
                        key=f"d{diente_num}",
                        label_visibility="collapsed"
                    )
                    if st.button("💾", key=f"b{diente_num}", use_container_width=True):
                        guardar_diente(id_paciente, diente_num, estado)
                        st.rerun()

        with tab2:
            st.subheader("Historial de Consultas y Pagos")
            if df_pacientes.empty:
                st.info("No hay pacientes registrados.")
            else:
                paciente_sel_hist = st.selectbox("Paciente", df_pacientes['nombre'].tolist(), key="hist_paciente")
                id_paciente_hist = df_pacientes[df_pacientes['nombre']==paciente_sel_hist]['id'].values[0]

                tab_citas, tab_pagos = st.tabs(["📅 Citas", "💰 Pagos"])

                with tab_citas:
                    # Tu código de citas actual aquí...
                    citas_paciente = supabase.table('citas')\
                    .select('*')\
                    .eq('id_paciente', int(id_paciente_hist))\
                    .order('fecha_cita', desc=True)\
                    .execute().data
                    df_citas_pac = pd.DataFrame(citas_paciente)
                    if df_citas_pac.empty:
                        st.info("Sin citas")
                    else:
                        st.dataframe(df_citas_pac, use_container_width=True, hide_index=True)

                with tab_pagos:
                    res_pagos = supabase.table('pagos')\
                    .select('*, abonos(*)')\
                    .eq('id_paciente', int(id_paciente_hist))\
                    .order('fecha_pago', desc=True)\
                    .execute()
                    
                    if not res_pagos.data:
                        st.info("Sin pagos registrados")
                    else:
                        for pago in res_pagos.data:
                            with st.container(border=True):
                                col1, col2 = st.columns([3,1])
                                with col1:
                                    fecha = pd.to_datetime(pago['fecha_pago']).strftime("%d/%m/%Y")
                                    st.markdown(f"**Pago #{pago['id']}** - {fecha}")
                                    st.caption(f"Tratamientos: {pago['concepto']}")
                                    if pago['descuento_valor'] > 0:
                                        st.caption(f"Subtotal: ${pago['subtotal']:,.2f} | Desc: -${pago['subtotal'] - pago['total']:,.2f}")
                                
                                with col2:
                                    st.metric("Total", f"${pago['total']:,.2f}")
                                    if pago['estatus'] == 'Pagado':
                                        st.success("✅ PAGADO")
                                    else:
                                        st.warning(f"⏳ Debe: ${pago['saldo_pendiente']:,.2f}")
                                
                                if pago['abonos']:
                                    with st.expander(f"Ver {len(pago['abonos'])} abonos"):
                                        for ab in pago['abonos']:
                                            fa = pd.to_datetime(ab['fecha_abono']).strftime("%d/%m/%Y")
                                            st.caption(f"• {fa} - ${ab['monto_abono']:,.2f} - {ab['metodo_pago']}")

# -------------------- 6. RECETAS --------------------
elif menu == "Recetas":
    st.header("Generar Receta Médica")
    df_pacientes = obtener_pacientes()
    if df_pacientes.empty:
        st.warning("Registra pacientes primero")
    else:
        if 'medicamentos_receta' not in st.session_state:
            st.session_state.medicamentos_receta = []

        col1, col2 = st.columns(2)
        with col1:
            paciente_sel = st.selectbox("Paciente", df_pacientes['nombre'].tolist())
            paciente_data = df_pacientes[df_pacientes['nombre']==paciente_sel].iloc[0]
        with col2:
            # CAMBIO 3: Calcular edad desde fecha_nacimiento
            edad_calc = calcular_edad(datetime.fromisoformat(paciente_data['fecha_nacimiento']).date()) if paciente_data.get('fecha_nacimiento') else "N/A"
            st.metric("Edad", f"{edad_calc} años" if edad_calc!= "N/A" else "N/A")
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

                    # CAMBIO 3: Usar edad calculada en el PDF
                    edad_pdf = edad_calc if edad_calc!= "N/A" else 0
                    pdf = generar_receta_pdf_varios(
                        paciente_sel,
                        int(edad_pdf),
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