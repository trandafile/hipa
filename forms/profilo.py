import streamlit as st
import pandas as pd
from core.google_api import g_api

def show_profilo():
    st.header("👤 Il tuo Profilo e Progetti di Ricerca")
    
    # Dati Utente Base (Solo Lettura per ora, o modificabili se richiesto)
    with st.expander("I tuoi Dati Personali", expanded=True):
         st.write(f"**Nome:** {st.session_state.get('user_given_name', 'N/D')}")
         st.write(f"**Cognome:** {st.session_state.get('user_family_name', 'N/D')}")
         st.write(f"**Email:** {st.session_state.get('user_email', 'N/D')}")
         st.write(f"**Ruolo di Sistema:** {st.session_state.get('user_role', 'Richiedente')}")
         
    st.divider()
    
    # Sezione Progetti
    st.header("📁 I tuoi Progetti di Ricerca")
    st.write("Aggiungi i progetti di cui sei titolare (o delegato) per poterli selezionare rapidamente durante la compilazione delle pratiche.")
    
    email = st.session_state.get('user_email')
    
    # 1. Lettura Progetti dal DB
    progetti_data = g_api.get_sheet_data('Progetti_Utenti')
    
    # Filtriamo solo i progetti di questo utente
    miei_progetti = [p for p in progetti_data if str(p.get('Email_Utente', '')).lower() == str(email).lower()]
    
    # 2. Tabella Progetti Esistenti
    if miei_progetti:
         df = pd.DataFrame(miei_progetti)
         # Rinomina colonne per la display se necessario
         st.dataframe(df[['Nome_Progetto', 'Acronimo', 'CUP']], use_container_width=True, hide_index=True)
    else:
         st.info("Nessun progetto caricato. Usare il form sottostante per aggiungerne uno.")
         
    # 3. Form Aggiunta Nuovo Progetto
    with st.form("add_project_form", clear_on_submit=True):
         st.subheader("Aggiungi Nuovo Progetto")
         col1, col2 = st.columns(2)
         with col1:
             nome_progetto = st.text_input("Nome Progetto (Completo)*")
             acronimo = st.text_input("Acronimo")
         with col2:
             cup = st.text_input("Codice CUP*")
             
         submitted = st.form_submit_button("Salva Progetto")
         
         if submitted:
             if not nome_progetto or not cup:
                 st.error("Nome Progetto e CUP sono campi obbligatori.")
             else:
                 new_id = len(progetti_data) + 1
                 row = [
                     new_id,
                     email,
                     nome_progetto,
                     acronimo,
                     cup
                 ]
                 
                 if g_api.append_row('Progetti_Utenti', row):
                      st.success(f"Progetto '{acronimo or nome_progetto}' aggiunto con successo!")
                      st.rerun()
