import streamlit as st
import datetime
import json
from core.google_api import g_api

def show_contratti_form(progetti_disp):
    st.header("Form: Nuova Richiesta di Contratto")
    
    opzioni_progetti = ["-- Seleziona un Progetto --"] + [f"{p['Nome_Progetto']} ({p['Acronimo']}) - CUP: {p['CUP']}" for p in progetti_disp]
    
    with st.form("richiesta_contratto_form"):
        st.subheader("1. Riferimenti Finanziari")
        progetto_sel = st.selectbox("Progetto di afferenza", opzioni_progetti)
        
        st.subheader("2. Dettagli Contratto")
        contraente = st.text_input("Soggetto Contraente/Azienda", required=True)
        oggetto = st.text_area("Oggetto del Contratto (dettagliato)", required=True)
        
        col1, col2 = st.columns(2)
        with col1:
             importo_netto = st.number_input("Importo (Netto in €)", min_value=0.0, format="%.2f", step=100.0)
        with col2:
             durata_mesi = st.number_input("Durata prevista (in mesi)", min_value=1, step=1)
             
        st.subheader("3. Modalità ed Eccezioni")
        tipo_contratto = st.selectbox("Tipologia di Contratto", [
             "Accordo di Collaborazione",
             "Contratto di Ricerca",
             "Conto Terzi",
             "Altro"
        ])
        
        note_aggiuntive = st.text_area("Note o richieste particolari per l'Ufficio Contratti")
        
        invio = st.form_submit_button("Invia Pratica", type="primary")

        if invio:
             if progetto_sel == opzioni_progetti[0]:
                  st.error("Devi selezionare un progetto.")
             elif not contraente or not oggetto:
                  st.error("I campi Contraente e Oggetto sono obbligatori.")
             else:
                  # Costruisci il JSON per i Dati Dinamici Form
                  dati_json = {
                      "progetto_string": progetto_sel,
                      "contraente": contraente,
                      "oggetto": oggetto,
                      "importo_netto": importo_netto,
                      "durata_mesi": durata_mesi,
                      "tipo_contratto": tipo_contratto,
                      "note_aggiuntive": note_aggiuntive
                  }
                  
                  salva_pratica_contratto("Contratti", dati_json)

def salva_pratica_contratto(tipo: str, dati_json: dict):
    pratiche_data = g_api.get_sheet_data('Pratiche')
    new_id = f"PR-{datetime.datetime.now().strftime('%Y%m')}-{len(pratiche_data) + 1:04d}"
    data_creazione = str(datetime.datetime.now())
    email_richiedente = st.session_state['user_email']
    
    # 1. Row to append in 'Pratiche'
    row_pratica = [
         new_id,
         email_richiedente,
         "", # Email_Operatore
         tipo,
         "Nuova Inserita", # Stato Attuale
         json.dumps(dati_json, ensure_ascii=False),
         "", # Note_Condivise vuote all'inizio
         data_creazione,
         "" # Link ZIP vuoto
    ]
    
    # 2. Row to append in 'Storico_Fasi'
    storico_data = g_api.get_sheet_data('Storico_Fasi')
    hist_id = len(storico_data) + 1
    row_storico = [
         hist_id,
         new_id,
         "Inserimento Iniziale", # Fase
         data_creazione,
         "", # Data Fine Vuota
         "FALSE" # Sospensione
    ]
    
    if g_api.append_row('Pratiche', row_pratica) and g_api.append_row('Storico_Fasi', row_storico):
         st.success(f"Pratica di tipo Contratto ({new_id}) registrata con successo! Verrai rediretto alla dashboard.")
         if st.button("Torna alla Dashboard"):
               st.session_state['current_page'] = "Dashboard"
               st.rerun()
