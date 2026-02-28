import streamlit as st
import pandas as pd
from core.google_api import g_api
import json

def show_profilo():
    st.header("👤 Il tuo Profilo e Progetti di Ricerca")
    
    # Dati Utente Base
    with st.expander("I tuoi Dati Personali", expanded=True):
         st.write(f"**Nome:** {st.session_state.get('user_given_name', 'N/D')}")
         st.write(f"**Cognome:** {st.session_state.get('user_family_name', 'N/D')}")
         st.write(f"**Email:** {st.session_state.get('user_email', 'N/D')}")
         st.write(f"**Ruolo di Sistema:** {st.session_state.get('user_role', 'Richiedente')}")
         
    st.divider()
    
    # Sezione Progetti
    st.header("📁 I tuoi Progetti di Ricerca")
    st.write("Gestioni i tuoi progetti per la compilazione rapida delle pratiche.")
    
    email = st.session_state.get('user_email')
    
    # 1. Lettura Progetti dal DB
    progetti_data = g_api.get_sheet_data('Progetti_Utenti')
    miei_progetti = [p for p in progetti_data if str(p.get('Email_Utente', '')).lower() == str(email).lower()]
    
    # 2. Visualizzazione e Azioni
    if miei_progetti:
         df = pd.DataFrame(miei_progetti)
         col_map = {
             'ID': 'ID',
             'Nome_Progetto': 'Nome Progetto',
             'Codice_CUP': 'CUP',
             'Responsabile_Scientifico': 'Responsabile'
         }
         df_display = df[list(col_map.keys())].rename(columns=col_map)
         st.dataframe(df_display, use_container_width=True, hide_index=True)
         
         # Sezione Modifica
         with st.expander("📝 Modifica un Progetto"):
             sel_prog_mod = st.selectbox("Seleziona Progetto da modificare", 
                                         options=[p['ID'] for p in miei_progetti],
                                         format_func=lambda x: next(p['Nome_Progetto'] for p in miei_progetti if p['ID'] == x),
                                         key="sel_mod")
             prog_mod = next(p for p in miei_progetti if p['ID'] == sel_prog_mod)
             
             with st.form("edit_project_form"):
                 new_nome = st.text_input("Nome Progetto", value=prog_mod['Nome_Progetto'])
                 new_cup = st.text_input("Codice CUP", value=prog_mod['Codice_CUP'])
                 new_resp = st.text_input("Responsabile Scientifico", value=prog_mod['Responsabile_Scientifico'])
                 
                 if st.form_submit_button("Salva Modifiche"):
                     if not new_nome or not new_cup:
                         st.error("Nome e CUP sono obbligatori.")
                     else:
                         row_idx = None
                         for i, p in enumerate(progetti_data):
                             if p['ID'] == sel_prog_mod:
                                 row_idx = i + 2
                                 break
                         
                         if row_idx:
                             g_api.update_cell('Progetti_Utenti', row_idx, 3, new_nome)
                             g_api.update_cell('Progetti_Utenti', row_idx, 4, new_cup)
                             g_api.update_cell('Progetti_Utenti', row_idx, 5, new_resp)
                             st.success("Progetto aggiornato!")
                             st.rerun()

         # Sezione Cancellazione
         with st.expander("❌ Elimina un Progetto"):
             prog_da_eliminare = st.selectbox("Seleziona Progetto da rimuovere", 
                                              options=[p['ID'] for p in miei_progetti],
                                              format_func=lambda x: next(p['Nome_Progetto'] for p in miei_progetti if p['ID'] == x),
                                              key="sel_del")
             if st.button("Elimina Definitivamente", type="secondary"):
                 if g_api.delete_row_by_id('Progetti_Utenti', 'ID', prog_da_eliminare):
                      st.success("Progetto eliminato.")
                      st.rerun()
    else:
         st.info("Nessun progetto caricato.")
         
    st.divider()

    # 3. Form Aggiunta Nuovo Progetto
    with st.form("add_project_form", clear_on_submit=True):
         st.subheader("➕ Aggiungi Nuovo Progetto")
         col1, col2 = st.columns(2)
         with col1:
             nome_p = st.text_input("Nome Progetto*")
             resp = st.text_input("Responsabile Scientifico", help="Lascia vuoto se sei tu")
         with col2:
             cup = st.text_input("Codice CUP*")
             
         submitted = st.form_submit_button("Salva Progetto")
         
         if submitted:
             if not nome_p or not cup:
                 st.error("Nome Progetto e CUP sono obbligatori.")
             else:
                 resp_final = resp if resp else f"{st.session_state.get('user_given_name')} {st.session_state.get('user_family_name')}"
                 new_id = len(progetti_data) + 1
                 # Schema: ["ID", "Email_Utente", "Nome_Progetto", "Codice_CUP", "Responsabile_Scientifico"]
                 row = [new_id, email, nome_p, cup, resp_final]
                 if g_api.append_row('Progetti_Utenti', row):
                      st.success(f"Progetto '{nome_p}' aggiunto!")
                      st.rerun()
