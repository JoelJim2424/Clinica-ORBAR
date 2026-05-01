import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, date, time
from fpdf import FPDF
import io
from streamlit_calendar import calendar

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
    *, h1, h2, h3, h4, h5, h6, p, label, span, div {
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

def insertar_cita(id_paciente, fecha_cita, hora_cita, dentista, motivo):
    return supabase.table('citas').insert({
        "id_paciente": id_paciente, "fecha_cita": str(fecha_cita), 
        "hora_cita": str(hora_cita), "dentista": dentista, "motivo": motivo
    }).execute().data[0]

def actualizar_estatus_cita(id_cita, estatus):
    supabase.table('citas').update({"estatus": estatus}).eq('id', id_cita).execute()

def obtener_tratamientos():
    return pd.DataFrame(supabase.table('tratamientos').select("*").order('nombre').execute().data)

def insertar_tratamiento(nombre, precio, descripcion):
    supabase.table('tratamientos').insert({"nombre": nombre, "precio": precio, "descripcion": descripcion}).execute()

def insertar_pago(id_paciente, id_cita, concepto, monto):
    supabase.table('pagos').insert({
        "id_paciente": id_paciente, "id_cita": id_cita, 
        "concepto": concepto, "monto": monto
    }).execute()

def insertar_historial(id_cita, diagnostico, procedimiento, observaciones):
    supabase.table('historial').insert({
        "id_cita": id_cita, "diagnostico": diagnostico, 
        "procedimiento": procedimiento, "observaciones": observaciones
    }).execute()

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

def guardar_diente(id_paciente, diente, estado):
    supabase.table('odontograma').delete().eq('id_paciente', id_paciente).eq('diente', diente).execute()
    if estado!= 'Sano':
        supabase.table('odontograma').insert({"id_paciente": id_paciente, "diente": diente, "estado": estado}).execute()

def obtener_odontograma(id_paciente):
    return pd.DataFrame(supabase.table('odontograma').select("*").eq('id_paciente', id_paciente).execute().data)

def insertar_receta(id_paciente, id_cita, medicamento, dosis, indicaciones):
    supabase.table('recetas').insert({
        "id_paciente": id_paciente, "id_cita": id_cita,
        "medicamento": medicamento, "dosis": dosis, "indicaciones": indicaciones
    }).execute()

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
    pdf.cell(0, 10, 'R E C E T A M É D I C A', 0, 1, 'C')
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
    
    return pdf.output(dest='S').encode('latin-1')

def generar_recibo_pdf(nombre_paciente, concepto, monto):
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
    pdf.cell(0, 10, "___________________________", ln=True, align="C")
    pdf.cell(0, 10, "Firma y Sello", ln=True, align="C")
    return pdf.output(dest='S').encode('latin-1')

# ==================== MENÚ PRINCIPAL ====================
st.sidebar.title("🦷 Clinica Dental ORBAR")
menu = st.sidebar.selectbox("Módulo", ["Agenda", "Pacientes", "Tratamientos", "Pagos", "Historial Clínico", "Recetas"])

# -------------------- 1. AGENDA --------------------
if menu == "Agenda":
    st.header("Agenda de Citas")
    tab1, tab2, tab3 = st.tabs(["Calendario", "Agendar Cita", "Atender Cita"])
    
    with tab1:
        df_citas = obtener_citas()
        if not df_citas.empty:
            events = []
            for _, row in df_citas.iterrows():
                color = "#4CAF50" if row['estatus']=='Atendida' else "#F44336" if row['estatus']=='Cancelada' else "#26A69A"
                events.append({
                    "id": str(row['id']),
                    "title": f"{row['pacientes']['nombre']} - {row['motivo']}",
                    "start": f"{row['fecha_cita']}T{row['hora_cita']}",
                    "color": color
                })
            calendar(events=events, options={"initialView": "dayGridMonth", "locale": "es", "height": 600})
        else:
            st.info("No hay citas programadas")
    
    with tab2:
        df_pacientes = obtener_pacientes()
        if df_pacientes.empty:
            st.warning("Primero registra un paciente en el módulo Pacientes")
        else:
            with st.form("form_cita"):
                paciente_sel = st.selectbox("Paciente*", df_pacientes['nombre'].tolist())
                id_paciente = df_pacientes[df_pacientes['nombre']==paciente_sel]['id'].values[0]
                col1, col2 = st.columns(2)
                with col1: fecha = st.date_input("Fecha*", min_value=date.today())
                with col2: hora = st.time_input("Hora*", value=time(9,0))
                dentista = st.selectbox("Dentista*", ["Dra. Zurisadai Orozco Barbina"])
                motivo = st.text_input("Motivo de consulta")
                if st.form_submit_button("Agendar Cita"):
                    insertar_cita(id_paciente, fecha, hora, dentista, motivo)
                    st.success("Cita agendada correctamente")
                    st.rerun()
    
    with tab3:
        df_citas_pend = obtener_citas()
        df_citas_pend = df_citas_pend[df_citas_pend['estatus'] == 'Programada'] if not df_citas_pend.empty else pd.DataFrame()
        if df_citas_pend.empty:
            st.info("No hay citas pendientes por atender")
        else:
            cita_sel = st.selectbox("Selecciona cita a atender", df_citas_pend.apply(lambda x: f"{x['pacientes']['nombre']} - {x['fecha_cita']} {x['hora_cita']}", axis=1))
            id_cita = df_citas_pend[df_citas_pend.apply(lambda x: f"{x['pacientes']['nombre']} - {x['fecha_cita']} {x['hora_cita']}", axis=1) == cita_sel]['id'].values[0]
            
            with st.form("form_atender"):
                diagnostico = st.text_area("Diagnóstico*")
                procedimiento = st.text_area("Procedimiento realizado*")
                observaciones = st.text_area("Observaciones")
                if st.form_submit_button("Guardar y Marcar como Atendida"):
                    insertar_historial(id_cita, diagnostico, procedimiento, observaciones)
                    actualizar_estatus_cita(id_cita, "Atendida")
                    st.success("Cita atendida y guardada en historial")
                    st.rerun()

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

# -------------------- 3. TRATAMIENTOS --------------------
elif menu == "Tratamientos":
    st.header("Catálogo de Tratamientos")
    tab1, tab2 = st.tabs(["Lista", "Agregar Tratamiento"])
    df_trat = obtener_tratamientos()
    
    with tab1:
        st.dataframe(df_trat, use_container_width=True, hide_index=True)
    
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
        with st.form("form_pago"):
            paciente_sel = st.selectbox("Paciente*", df_pacientes['nombre'].tolist())
            id_paciente = df_pacientes[df_pacientes['nombre']==paciente_sel]['id'].values[0]
            trat_sel = st.selectbox("Tratamiento*", df_trat['nombre'].tolist())
            monto = df_trat[df_trat['nombre']==trat_sel]['precio'].values[0]
            st.metric("Monto a Pagar", f"${monto:,.2f} MXN")
            if st.form_submit_button("Registrar Pago y Generar Recibo"):
                insertar_pago(id_paciente, None, trat_sel, monto)
                pdf = generar_recibo_pdf(paciente_sel, trat_sel, monto)
                st.success("Pago registrado correctamente")
                st.download_button("📄 Descargar Recibo PDF", pdf, f"Recibo_{paciente_sel}.pdf", "application/pdf")

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
            df_hist = obtener_historial(id_paciente)
            if not df_hist.empty:
                st.dataframe(df_hist[['fecha_cita', 'motivo', 'diagnostico', 'procedimiento', 'observaciones']], use_container_width=True, hide_index=True)
            else:
                st.info("Este paciente no tiene consultas registradas aún")

# -------------------- 6. RECETAS --------------------
elif menu == "Recetas":
    st.header("Generar Receta Médica")
    df_pacientes = obtener_pacientes()
    if df_pacientes.empty:
        st.warning("Registra pacientes primero")
    else:
        with st.form("form_receta"):
            col1, col2 = st.columns(2)
            with col1:
                paciente_sel = st.selectbox("Paciente*", df_pacientes['nombre'].tolist())
                paciente_data = df_pacientes[df_pacientes['nombre']==paciente_sel].iloc[0]
            with col2:
                st.metric("Edad", f"{int(paciente_data['edad'])} años")
                st.metric("Alergias", paciente_data['alergias'] if paciente_data['alergias'] else "Ninguna")
            
            st.divider()
            medicamento = st.text_input("Medicamento*", placeholder="Ej: Amoxicilina 500mg")
            dosis = st.text_input("Dosis*", placeholder="Ej: 1 cápsula cada 8 horas")
            indicaciones = st.text_area("Indicaciones", placeholder="Ej: Tomar después de alimentos por 7 días. No suspender tratamiento.")
            
            if st.form_submit_button("Generar Receta PDF"):
                if medicamento and dosis:
                    insertar_receta(paciente_data['id'], None, medicamento, dosis, indicaciones)
                    pdf = generar_receta_pdf(paciente_sel, int(paciente_data['edad']), medicamento, dosis, indicaciones)
                    st.success("Receta generada correctamente")
                    st.download_button("📄 Descargar Receta PDF", pdf, f"Receta_{paciente_sel}_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf")
                else:
                    st.error("Medicamento y dosis son obligatorios")