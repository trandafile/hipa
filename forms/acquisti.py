import streamlit as st
import datetime
import json
from core.google_api import g_api
from core.pdf_generator import genera_pdf_pratica
from forms.dashboard import autoassegna_operatore

def show_acquisti_form(progetti_disp):
    st.header("Form: Nuova Richiesta di Acquisto")
    
    # Inizializza step e dati in session_state
    if 'acquisti_step' not in st.session_state:
        st.session_state['acquisti_step'] = 1
    if 'acquisti_data' not in st.session_state:
        st.session_state['acquisti_data'] = {}
    if 'acquisti_pdf' not in st.session_state:
        st.session_state['acquisti_pdf'] = None

    # Prepara la lista progetti (Dropdown)
    opzioni_progetti = ["-- Seleziona un Progetto --"] + [f"{p['Nome_Progetto']} - CUP: {p.get('Codice_CUP', 'N/D')}" for p in progetti_disp]
    
    if st.session_state['acquisti_step'] == 1:
        with st.form("richiesta_acquisto_form"):
            st.subheader("1. Informazioni Generali")
            titolo = st.text_input("Titolo Pratica (Breve)", value=st.session_state['acquisti_data'].get('titolo', ''))
            
            # Trova indice progetto precedente se esiste
            idx_p = 0
            if 'progetto_string' in st.session_state['acquisti_data']:
                try: idx_p = opzioni_progetti.index(st.session_state['acquisti_data']['progetto_string'])
                except: pass
            
            progetto_sel = st.selectbox("Progetto di afferenza", opzioni_progetti, index=idx_p)
            
            st.subheader("2. Dettagli Bene o Servizio")
            oggetto = st.text_area("Oggetto dell'Acquisto (Descrizione dettagliata)", value=st.session_state['acquisti_data'].get('oggetto', ''))
            cpv = st.text_input("Codice CPV (opzionale se non noto)", value=st.session_state['acquisti_data'].get('cpv', ''))
            motivazioni = st.text_area("Motivazioni e coerenza col progetto", value=st.session_state['acquisti_data'].get('motivazioni', ''))
            
            col1, col2 = st.columns(2)
            with col1:
                 importo_netto = st.number_input("Spesa Presunta (Netto in €)", min_value=0.0, format="%.2f", step=10.0, value=float(st.session_state['acquisti_data'].get('importo_netto', 0.0)))
            with col2:
                 iva_val = st.session_state['acquisti_data'].get('iva', "22%")
                 iva_opts = ["22%", "10%", "4%", "Esente (0%)"]
                 idx_iva = iva_opts.index(iva_val) if iva_val in iva_opts else 0
                 iva = st.selectbox("Aliquota IVA", iva_opts, index=idx_iva)
                 
            # Calcolo Totale Presunto
            perc_iva = int(iva.replace('%', '').replace('Esente (0)', '0'))
            totale = importo_netto + (importo_netto * (perc_iva / 100))
            st.markdown(f"**Totale Spesa Presunta (IVA inclusa): € {totale:.2f}**")
            
            st.subheader("3. Gestione Inventario")
            inv_val = st.session_state['acquisti_data'].get('inventariabile', "No")
            inventariabile = st.radio("Il bene è inventariabile?", ("No", "Sì"), index=0 if inv_val=="No" else 1)
            
            ubicazione = ""
            responsabilita = ""
            responsabile_testo = ""
            ammortamento = False
            
            if inventariabile == "Sì":
                 ubicazione = st.text_input("Ubicazione (Stanza n., Cubo n., Piano)", value=st.session_state['acquisti_data'].get('ubicazione', ''))
                 resp_val = st.session_state['acquisti_data'].get('responsabilita', "Sotto la responsabilità del sottoscritto")
                 responsabilita = st.radio("Assegnazione", ("Sotto la responsabilità del sottoscritto", "Assegnato a terzi"), index=0 if resp_val=="Sotto la responsabilità del sottoscritto" else 1)
                 if responsabilita == "Assegnato a terzi":
                      responsabile_testo = st.text_input("Nome/Cognome Assegnatario", value=st.session_state['acquisti_data'].get('assegnatario', ''))
                 ammortamento = st.checkbox("Ammortizzato in 36 mesi - 33,33%", value=st.session_state['acquisti_data'].get('ammortamento', False))
                 
            st.subheader("4. Documentazione")
            st.write("Puoi allegare preventivi o altra documentazione in formato PDF.")
            uploaded_files = st.file_uploader("Trascina qui i tuoi PDF", type=["pdf"], accept_multiple_files=True)
            
            crea_pdf = st.form_submit_button("Crea pdf per avvio pratica", type="primary")

            if crea_pdf:
                 if not titolo:
                      st.error("Il Titolo della Pratica è obbligatorio.")
                 elif progetto_sel == opzioni_progetti[0]:
                      st.error("Devi selezionare un progetto.")
                 elif not oggetto or not motivazioni:
                      st.error("I campi Oggetto e Motivazioni sono obbligatori.")
                 elif inventariabile == "Sì" and not ubicazione:
                      st.error("L'ubicazione è obbligatoria per i beni inventariabili.")
                 elif inventariabile == "Sì" and responsabilita == "Assegnato a terzi" and not responsabile_testo:
                      st.error("Devi indicare a chi è assegnato il bene.")
                 else:
                      # Salva i dati in session_state
                      acronimo = progetto_sel.split(' - CUP:')[0]
                      data_now = str(datetime.datetime.now())
                      
                      pending_data = {
                          "titolo": titolo,
                          'progetto_acronimo': acronimo,
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
                          "ammortamento": ammortamento if inventariabile == "Sì" else False,
                          "data_creazione": data_now
                      }
                      
                      # Genera PDF in memoria
                      pdf_bytes = genera_pdf_pratica(
                          pratica_id="BOZZA", # ID temporaneo
                          tipo="Acquisto",
                          richiedente=st.session_state['user_email'],
                          data_creazione=data_now,
                          stato_attuale="In attesa di firma",
                          dati_json=pending_data
                      )
                      
                      st.session_state['acquisti_data'] = pending_data
                      st.session_state['acquisti_pdf'] = pdf_bytes
                      st.session_state['acquisti_files'] = uploaded_files # File originali
                      st.session_state['acquisti_step'] = 2
                      st.rerun()

    elif st.session_state['acquisti_step'] == 2:
        st.success("✅ Dati validati con successo!")
        st.info("Scarica il modulo di riepilogo generato, firmalo e ricaricalo per inviare la pratica.")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                label="⬇️ Scarica Modulo di Sintesi (PDF)",
                data=st.session_state['acquisti_pdf'],
                file_name=f"Riepilogo_Acquisto_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
        
        with col_d2:
            if st.button("⬅️ Torna al Form"):
                st.session_state['acquisti_step'] = 1
                st.rerun()
        
        st.divider()
        st.subheader("5. Caricamento Modulo Firmato")
        modulo_firmato = st.file_uploader("Carica il PDF firmato", type=["pdf"], key="signed_pdf")
        
        if modulo_firmato:
            st.success("📄 Modulo firmato caricato correttamente.")
            if st.button("🚀 Invia Pratica", type="primary"):
                with st.spinner("Registrazione pratica e salvataggio file in corso..."):
                    # Passiamo anche il modulo firmato
                    new_id = salva_pratica(
                        "Acquisto", 
                        st.session_state['acquisti_data'], 
                        st.session_state['acquisti_files'], 
                        modulo_firmato=modulo_firmato,
                        user_creds=st.session_state.get('user_creds')
                    )
                    if new_id:
                        # Reset session state
                        del st.session_state['acquisti_step']
                        del st.session_state['acquisti_data']
                        del st.session_state['acquisti_pdf']
                        del st.session_state['acquisti_files']
                        
                        st.session_state['dashboard_message'] = f"Pratica {new_id} registrata con successo!"
                        st.session_state['current_page'] = "Pannello Richiedente"
                        st.rerun()

def salva_pratica(tipo: str, dati_json: dict, files: list, modulo_firmato=None, user_creds: str = None):
    pratiche_data = g_api.get_sheet_data('Pratiche')
    new_id = f"PR-{datetime.datetime.now().strftime('%Y%m')}-{len(pratiche_data) + 1:04d}"
    data_creazione = dati_json.get('data_creazione', str(datetime.datetime.now()))
    email_richiedente = st.session_state['user_email']
    
    # 1. Riga per 'Pratiche'
    op_assegnato = autoassegna_operatore(tipo)
    row_pratica = [
         new_id, tipo, email_richiedente,
         dati_json.get("progetto_acronimo", ""),
         dati_json.get("titolo", dati_json.get("oggetto", "")),
         dati_json.get("totale", 0.0),
         "Nuova Inserita", data_creazione, op_assegnato, 
         "", json.dumps(dati_json, ensure_ascii=False), ""
    ]
    
    # 2. Riga per 'Storico_Fasi'
    storico_data = g_api.get_sheet_data('Storico_Fasi')
    hist_id = len(storico_data) + 1
    row_storico = [hist_id, new_id, "Nuova Inserita", data_creazione, "", "Inserimento Iniziale"]
    
    # 3. Append Database
    if g_api.append_row('Pratiche', row_pratica) and g_api.append_row('Storico_Fasi', row_storico):
         # Carpella Drive
         tipo_folder_id = g_api.get_or_create_folder(tipo, user_creds_json=user_creds)
         pratica_folder_id = g_api.get_or_create_folder(new_id, parent_id=tipo_folder_id, user_creds_json=user_creds)

         # Allegati
         allegati_data = g_api.get_sheet_data('Allegati')
         all_id = len(allegati_data) + 1
         
         # 3a. Carica Modulo Firmato
         if modulo_firmato:
             link_m = g_api.upload_file(
                 modulo_firmato.getvalue(), 
                 file_name=f"{new_id}_Modulo_Richiesta_Firmato.pdf", 
                 mimetype="application/pdf",
                 folder_id=pratica_folder_id,
                 user_creds_json=user_creds
             )
             if link_m:
                 g_api.append_row('Allegati', [all_id, new_id, "Modulo_Richiesta_Firmato.pdf", link_m, str(datetime.datetime.now())])
                 all_id += 1

         # 3b. Carica Altri Allegati
         for f in files:
             link = g_api.upload_file(
                 f.getvalue(), 
                 file_name=f"{new_id}_{f.name}", 
                 mimetype="application/pdf",
                 folder_id=pratica_folder_id,
                 user_creds_json=user_creds
             )
             if link:
                 g_api.append_row('Allegati', [all_id, new_id, f.name, link, str(datetime.datetime.now())])
                 all_id += 1
                  
         return new_id
    return None
