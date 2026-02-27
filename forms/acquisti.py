import streamlit as st
import datetime
import json
from core.google_api import g_api

def show_acquisti_form(progetti_disp):
    st.header("Form: Nuova Richiesta di Acquisto")
    
    # Prepara la lista progetti (Dropdown)
    opzioni_progetti = ["-- Seleziona un Progetto --"] + [f"{p['Nome_Progetto']} ({p['Acronimo']}) - CUP: {p['CUP']}" for p in progetti_disp]
    
    with st.form("richiesta_acquisto_form"):
        st.subheader("1. Riferimenti Finanziari")
        progetto_sel = st.selectbox("Progetto di afferenza", opzioni_progetti)
        
        st.subheader("2. Dettagli Bene o Servizio")
        oggetto = st.text_area("Oggetto dell'Acquisto (Descrizione dettagliata)", required=True)
        cpv = st.text_input("Codice CPV (opzionale se non noto)")
        motivazioni = st.text_area("Motivazioni e coerenza col progetto", required=True)
        
        col1, col2 = st.columns(2)
        with col1:
             importo_netto = st.number_input("Spesa Presunta (Netto in €)", min_value=0.0, format="%.2f", step=10.0)
        with col2:
             iva = st.selectbox("Aliquota IVA", ["22%", "10%", "4%", "Esente (0%)"])
             
        # Calcolo Totale Presunto
        perc_iva = int(iva.replace('%', '').replace('Esente (0)', '0'))
        totale = importo_netto + (importo_netto * (perc_iva / 100))
        st.markdown(f"**Totale Spesa Presunta (Ivan inclusa): € {totale:.2f}**")
        
        st.subheader("3. Gestione Inventario")
        inventariabile = st.radio("Il bene è inventariabile?", ("No", "Sì"))
        
        ubicazione = ""
        responsabilita = ""
        responsabile_testo = ""
        ammortamento = False
        
        if inventariabile == "Sì":
             ubicazione = st.text_input("Ubicazione (Stanza n., Cubo n., Piano)", required=True)
             responsabilita = st.radio("Assegnazione", ("Sotto la responsabilità del sottoscritto", "Assegnato a terzi"))
             if responsabilita == "Assegnato a terzi":
                  responsabile_testo = st.text_input("Nome/Cognome Assegnatario", required=True)
             ammortamento = st.checkbox("Ammortizzato in 36 mesi - 33,33%")
        
        invio = st.form_submit_button("Invia Pratica", type="primary")

        if invio:
             if progetto_sel == opzioni_progetti[0]:
                  st.error("Devi selezionare un progetto.")
             elif not oggetto or not motivazioni:
                  st.error("I campi Oggetto e Motivazioni sono obbligatori.")
             elif inventariabile == "Sì" and not ubicazione:
                  st.error("L'ubicazione è obbligatoria per i beni inventariabili.")
             elif inventariabile == "Sì" and responsabilita == "Assegnato a terzi" and not responsabile_testo:
                  st.error("Devi indicare a chi è assegnato il bene.")
             else:
                  # Costruisci il JSON per i Dati Dinamici Form
                  dati_json = {
                      "progetto_string": progetto_sel,
                      "oggetto": oggetto,
                      "cpv": cpv,
                      "motivazioni": motivazioni,
                      "importo_netto": importo_netto,
                      "iva": iva,
                      "totale": totale,
                      "inventariabile": inventariabile,
                      "ubicazione": ubicazione if inventariabile == "Sì" else None,
                      "responsabilita": responsabilita if inventariabile == "Sì" else None,
                      "assegnatario": responsabile_testo if responsabilita == "Assegnato a terzi" else st.session_state['user_email'],
                      "ammortamento": ammortamento if inventariabile == "Sì" else False
                  }
                  
                  salva_pratica("Acquisto", dati_json)

def salva_pratica(tipo: str, dati_json: dict):
    pratiche_data = g_api.get_sheet_data('Pratiche')
    new_id = f"PR-{datetime.datetime.now().strftime('%Y%m')}-{len(pratiche_data) + 1:04d}"
    data_creazione = str(datetime.datetime.now())
    email_richiedente = st.session_state['user_email']
    
    # 1. Row to append in 'Pratiche'
    row_pratica = [
         new_id,
         email_richiedente,
         "", # Email_Operatore (da assegnare dal Dispatcher)
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
         st.success(f"Pratica {new_id} registrata con successo! Verrai rediretto alla dashboard.")
         # Aggiungi un flag o pulsante per resettare
         if st.button("Torna alla Dashboard"):
               st.session_state['current_page'] = "Dashboard"
               st.rerun()
