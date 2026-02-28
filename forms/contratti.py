import streamlit as st
import datetime
import json
from core.google_api import g_api
from forms.dashboard import autoassegna_operatore

def show_contratti_form(progetti_disp):
    st.header("Form: Nuova Richiesta di Contratto")
    
    # Flag per gestire lo stato post-invio
    if 'contratto_success_id' in st.session_state:
        st.success(f"Pratica {st.session_state['contratto_success_id']} registrata con successo!")
        if st.button("Torna alla Dashboard"):
            del st.session_state['contratto_success_id']
            st.session_state['current_page'] = "Pannello Richiedente"
            st.rerun()
        st.info("Vuoi inviare un'altra richiesta? Compila il form qui sotto.")
        st.divider()

    # Prepara la lista progetti (Dropdown)
    opzioni_progetti = ["-- Seleziona un Progetto --"] + [f"{p['Nome_Progetto']} - CUP: {p.get('Codice_CUP', 'N/D')}" for p in progetti_disp]
    
    pending_submit = None

    with st.form("richiesta_contratto_form"):
        st.subheader("1. Informazioni Generali")
        titolo = st.text_input("Titolo Pratica (Breve)")
        progetto_sel = st.selectbox("Progetto di afferenza", opzioni_progetti)
        
        st.subheader("2. Dettagli Contratto")
        contraente = st.text_input("Soggetto Contraente/Azienda")
        oggetto = st.text_area("Oggetto del Contratto (dettagliato)")
        
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
             if not titolo:
                  st.error("Il Titolo della Pratica è obbligatorio.")
             elif progetto_sel == opzioni_progetti[0]:
                  st.error("Devi selezionare un progetto.")
             elif not contraente or not oggetto:
                  st.error("I campi Contraente e Oggetto sono obbligatori.")
             else:
                  # Estrai acronimo
                  acronimo = progetto_sel.split(" - CUP:")[0]
                  pending_submit = {
                      "titolo": titolo,
                      "progetto_acronimo": acronimo,
                      "progetto_string": progetto_sel,
                      "contraente": contraente,
                      "oggetto": oggetto,
                      "importo_netto": importo_netto,
                      "durata_mesi": durata_mesi,
                      "tipo_contratto": tipo_contratto,
                      "note_aggiuntive": note_aggiuntive
                  }

    if pending_submit:
        new_id = salva_pratica_contratto("Contratti", pending_submit)
        if new_id:
            st.session_state['contratto_success_id'] = new_id
            st.rerun()

def salva_pratica_contratto(tipo: str, dati_json: dict):
    pratiche_data = g_api.get_sheet_data('Pratiche')
    new_id = f"PR-{datetime.datetime.now().strftime('%Y%m')}-{len(pratiche_data) + 1:04d}"
    data_creazione = str(datetime.datetime.now())
    email_richiedente = st.session_state['user_email']
    
    # 1. Row to append in 'Pratiche'
    # ["ID_Pratica", "Tipo", "Email_Richiedente", "Oggetto", "Importo", "Stato_Attuale", "Data_Creazione", "Email_Operatore", "Note_Condivise", "JSON_Dati"]
    op_assegnato = autoassegna_operatore(tipo)

    row_pratica = [
         new_id,
         tipo,
         email_richiedente,
         dati_json.get("progetto_acronimo", ""),
         dati_json.get("titolo", dati_json.get("oggetto", "")),
         dati_json.get("importo_netto", 0.0), # Per i contratti usiamo il netto come riferimento principale
         "Nuova Inserita", # Stato Attuale
         data_creazione,
         op_assegnato, # Email_Operatore (auto-assegnato o vuoto)
         "", # Note_Condivise vuote all'inizio
         json.dumps(dati_json, ensure_ascii=False),
         "" # Notifica_Nota
    ]
    
    # 2. Row to append in 'Storico_Fasi'
    storico_data = g_api.get_sheet_data('Storico_Fasi')
    hist_id = len(storico_data) + 1
    row_storico = [
         hist_id,
         new_id,
         "Nuova Inserita",
         data_creazione,
         "",
         "Inserimento Iniziale"
    ]
    
    if g_api.append_row('Pratiche', row_pratica) and g_api.append_row('Storico_Fasi', row_storico):
         return new_id
    return None
