import streamlit as st
import pandas as pd
import datetime
from core.google_api import g_api
from forms.dashboard import update_pratica_stato

def show_dettaglio_pratica():
    if 'pratica_selezionata' not in st.session_state:
        st.warning("Nessuna pratica selezionata.")
        if st.button("Torna alla Dashboard"):
            st.session_state['current_page'] = "Pannello Richiedente"
            st.rerun()
        return

    id_p = st.session_state['pratica_selezionata']
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.header(f"🔭 Dettaglio Pratica: {id_p}")
    with col2:
        if st.button("🔙 Torna alla Dashboard", use_container_width=True):
            del st.session_state['pratica_selezionata']
            st.session_state['current_page'] = "Pannello Richiedente"
            st.rerun()

    pratiche_data = g_api.get_sheet_data('Pratiche')
    pratica = next((p for p in pratiche_data if p['ID_Pratica'] == id_p), None)
    
    if not pratica:
        st.error("Dati pratica non trovati.")
        return

    st.subheader("Informazioni Generali")
    st.write(f"**Tipo:** {pratica.get('Tipo')}")
    st.write(f"**Progetto:** {pratica.get('Progetto', 'N/D')}")
    st.write(f"**Richiedente:** {pratica.get('Email_Richiedente')}")
    st.write(f"**Stato Attuale:** {pratica.get('Stato_Attuale')}")
    st.write(f"**Operatore Assegnato:** {pratica.get('Email_Operatore', 'Nessuno')}")
    st.write(f"**Oggetto:** {pratica.get('Oggetto')}")

    # --- Reset Notifica se presente ---
    user_email = str(st.session_state.get('user_email', '')).lower().strip()
    req_email = str(pratica.get('Email_Richiedente', '')).lower().strip()
    notif = str(pratica.get('Notifica_Nota', '')).strip()
    det_context = st.session_state.get('det_context', 'richiedente')
    
    clear_notif = False
    # Se la notifica è per il Richiedente e il contesto è Richiedente
    if notif == 'Richiedente' and det_context == 'richiedente':
        clear_notif = True
    # Se la notifica è per l'Operatore e il contesto è Operatore
    elif notif == 'Operatore' and det_context == 'operatore':
        clear_notif = True
        
    if clear_notif:
        row_idx = next((i + 2 for i, r in enumerate(pratiche_data) if r['ID_Pratica'] == id_p), None)
        if row_idx:
            g_api.update_cell('Pratiche', row_idx, 11, "")

    st.divider()
    
    # --- Azioni ---
    ruolo = str(st.session_state.get('user_role', '')).lower()
    stato_attuale = pratica.get('Stato_Attuale')
    
    # Mostriamo i bottoni solo se rilevanti
    if (ruolo == 'richiedente' and stato_attuale in ['Nuova Inserita', 'Non preso in carico']) or (ruolo in ['admin', 'worker', 'dispatcher'] and stato_attuale != 'Archiviata'):
         st.subheader("⚡ Azioni Rapide")
         col_az1, col_az2, _ = st.columns([2, 2, 6])
         
         with col_az1:
              if ruolo == 'richiedente' and stato_attuale in ['Nuova Inserita', 'Non preso in carico']:
                   if st.button("❌ Annulla / Elimina Pratica", type="primary"):
                        if g_api.delete_row_by_id('Pratiche', 'ID_Pratica', id_p):
                             del st.session_state['pratica_selezionata']
                             st.session_state['dashboard_message'] = "Pratica eliminata con successo!"
                             st.session_state['current_page'] = "Pannello Richiedente"
                             st.rerun()
         
         with col_az2:
              if ruolo in ['admin', 'worker', 'dispatcher'] and stato_attuale != 'Archiviata':
                   if st.button("🗃️ Archivia Pratica"):
                        update_pratica_stato(id_p, "Archiviata", "Archiviazione forzata tramite azione rapida")
                        st.session_state['dashboard_message'] = f"Pratica {id_p} archiviata."
                        st.rerun()

              if ruolo in ['admin', 'worker', 'dispatcher'] and stato_attuale in ['Archiviata', 'Conclusa']:
                   if st.button("🔓 Riapri Pratica", type="primary"):
                        update_pratica_stato(id_p, "In lavorazione", "Riapertura pratica tramite azione rapida")
                        st.session_state['dashboard_message'] = f"Pratica {id_p} riaperta con successo."
                        st.rerun()
    st.divider()

    # --- Cronistoria Fasi ---
    st.subheader("⏱️ Cronistoria Fasi")
    # CSS specifico per le righe alternate nel dettaglio
    st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"]:nth-of-type(even) { background-color: #f9f9f0; border-radius: 4px; }
        div[data-testid="stHorizontalBlock"]:nth-of-type(odd) { background-color: #ffffff; border-radius: 4px; }
        </style>
    """, unsafe_allow_html=True)

    storico_data = g_api.get_sheet_data('Storico_Fasi')
    fasi_pratica = [f for f in storico_data if f['ID_Pratica'] == id_p]
    if fasi_pratica:
        # Header manuale
        h1, h2, h3 = st.columns([3, 3, 4])
        h1.write("**Stato**")
        h2.write("**Data**")
        h3.write("**Note**")
        st.divider()
        
        for f in fasi_pratica:
            r1, r2, r3 = st.columns([3, 3, 4])
            # La zebra stripe funzionerà grazie al CSS iniettato prima se miriamo gli horizontal blocks
            r1.write(f['Stato'])
            r2.write(str(f['Data_Inizio'])[:16])
            r3.write(f['Note'])
    else:
        st.info("Nessuna fase registrata.")

    st.divider()

    # --- Allegati ---
    st.subheader("📎 Documenti e Allegati")
    allegati_data = g_api.get_sheet_data('Allegati')
    allegati_pratica = [a for a in allegati_data if a['ID_Pratica'] == id_p]
    
    if allegati_pratica:
        for a in allegati_pratica:
            st.markdown(f"- [{a['Nome_File']}]({a['Drive_Link']}) (Caricato il: {a['Timestamp']})")
    else:
        st.info("Nessun allegato presente.")
        
    st.write("Aggiungi un nuovo allegato (solo se richiesto):")
    uploaded_file = st.file_uploader("Carica File", key="upload_dettaglio")
    if st.button("Carica e Allega"):
        if uploaded_file:
            with st.spinner("Caricamento in corso..."):
                # Trova/Crea folder hierarchy: Tipo / ID_Pratica
                tp = pratica.get('Tipo', 'Acquisti')
                creds = st.session_state.get('user_creds')
                tipo_f_id = g_api.get_or_create_folder(tp, user_creds_json=creds)
                pratica_f_id = g_api.get_or_create_folder(id_p, parent_id=tipo_f_id, user_creds_json=creds)

                link = g_api.upload_file(
                    uploaded_file.getvalue(), 
                    f"{id_p}_{uploaded_file.name}", 
                    "application/pdf",
                    folder_id=pratica_f_id,
                    user_creds_json=creds
                )
                if link:
                     all_id = len(g_api.get_sheet_data('Allegati')) + 1
                     g_api.append_row('Allegati', [all_id, id_p, uploaded_file.name, link, str(datetime.datetime.now())])
                     st.success("Allegato caricato!")
                     st.rerun()
        else:
            st.warning("Seleziona prima un file.")

    # --- Gestione Stato (Solo Operatore/Admin) ---
    if ruolo in ['admin', 'worker', 'dispatcher']:
        st.divider()
        st.subheader("⚙️ Gestione Stato e Avanzamento")
        
        tipo_pratica = pratica.get('Tipo', 'Acquisto')
        if tipo_pratica == "Acquisto":
            stati_opzioni = [
                "Non preso in carico",
                "Fase 1: verifica documentazione",
                "Fase 2: ordine trasmesso al fornitore",
                "In attesa di riscontri",
                "Conclusa"
            ]
        elif tipo_pratica == "Contratti di Ricerca / Incarichi":
            stati_opzioni = [
                "Non preso in carico",
                "In lavorazione",
                "Fase 1: verifica requisiti",
                "Fase 2: bozza contratto",
                "In attesa di firma",
                "Conclusa"
            ]
        else:
            stati_opzioni = ["In lavorazione", "In attesa di riscontri", "Conclusa"]
            
        # Determiniamo l'indice dello stato attuale se possibile
        try:
            val_stat = str(pratica.get('Stato_Attuale', ''))
            idx_attuale = stati_opzioni.index(val_stat) if val_stat in stati_opzioni else 0
        except:
            idx_attuale = 0
            
        with st.form("form_aggiorna_stato_dettaglio"):
            nuovo_s = st.selectbox("Cambia Stato / Fase", stati_opzioni, index=idx_attuale)
            nota_stato = st.text_area("Nota per l'aggiornamento (opzionale, visibile al richiedente)", help="Verrà aggiunta alla cronistoria e alle note condivise")
            
            if st.form_submit_button("Aggiorna Stato", type="primary"):
                update_pratica_stato(id_p, nuovo_s, nota_stato)
                st.session_state['dashboard_message'] = f"Stato pratica {id_p} aggiornato a {nuovo_s}."
                st.rerun()

    st.divider()

    # --- Note (Conversazione) ---
    st.subheader("💬 Note e Comunicazioni")
    note_condivise = pratica.get('Note_Condivise', "")
    if note_condivise:
        for nota in note_condivise.split('\n'):
            if nota.strip():
                # Formattazione base chat message
                if "Sconosciuto" not in nota:
                     st.info(nota.strip())
                else:
                     st.write(nota.strip())
    else:
        st.info("Nessuna nota presente.")
        
    nuova_nota = st.text_area("Aggiungi una nuova nota alla pratica:", key="nuova_nota_testo")
    if st.button("Invia Nota"):
         if nuova_nota:
              autore = st.session_state.get('user_email', 'Utente')
              timestamp = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
              testo_completo = f"[{timestamp}] {autore}: {nuova_nota}"
              
              nota_aggiornata = f"{note_condivise}\n{testo_completo}" if note_condivise else testo_completo
              
              # Trova riga per fare update_cell in 'Pratiche'
              row_idx = None
              for i, r in enumerate(pratiche_data):
                  if r['ID_Pratica'] == id_p:
                       row_idx = i + 2
                       break
              if row_idx:
                  # Determina a chi va la notifica in base al contesto in cui si trova l'utente
                  det_context = st.session_state.get('det_context', 'richiedente')
                  
                  if det_context == 'richiedente':
                       destinatario_notifica = "Operatore"
                  else:
                       destinatario_notifica = "Richiedente"
                  
                  g_api.update_cell('Pratiche', row_idx, 9, nota_aggiornata)
                  g_api.update_cell('Pratiche', row_idx, 11, destinatario_notifica)
                  st.success("Nota aggiunta!")
                  st.rerun()
         else:
             st.warning("Scrivi qualcosa prima di inviare.")
