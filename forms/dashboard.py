import streamlit as st
import pandas as pd
from core.google_api import g_api

def show_dashboard():
    st.header("🗂️ Cruscotto Pratiche")
    
    role = st.session_state.get('user_role', 'Richiedente')
    email = st.session_state.get('user_email', '')
    
    if role == 'Richiedente':
         show_richiedente_dashboard(email)
    elif role == 'Worker':
         show_worker_dashboard(email)
    elif role == 'Dispatcher':
         show_dispatcher_dashboard()
    elif role == 'Admin':
         show_admin_dashboard()
    else:
         st.error(f"Ruolo sconosciuto: {role}")

def show_richiedente_dashboard(email):
    st.write("Le tue pratiche attive e lo storico.")
    # Logica recupero pratiche per il richiedente
    pratiche_data = g_api.get_sheet_data('Pratiche')
    mie_pratiche = [p for p in pratiche_data if str(p.get('Email_Richiedente', '')).lower() == str(email).lower()]
    
    if not mie_pratiche:
        st.info("Non hai nessuna pratica attiva.")
    else:
        df = pd.DataFrame(mie_pratiche)
        st.dataframe(df[['ID_Pratica', 'Tipo', 'Stato_Attuale', 'Data_Creazione']], use_container_width=True, hide_index=True)

def update_pratica_operatore(id_pratica, new_operator_email):
    """Stub function to update the assigned operator of a ticket"""
    # Requires finding the row index in the 'Pratiche' sheet and calling update_cell
    # For now, we will simulate the functionality or rely on a generic update_row_by_id in google_api
    st.warning(f"Assegnazione {id_pratica} a {new_operator_email} - Da completare lato DB")
    # In a real implementation: g_api.update_cell('Pratiche', row_idx, col_idx_operatore, new_operator_email)

def update_pratica_stato(id_pratica, nuovo_stato):
    """Stub function to update the status of a ticket"""
    st.warning(f"Aggiornamento {id_pratica} a {nuovo_stato} - Da completare lato DB")

def show_worker_dashboard(email):
    st.write("Pratiche assegnate a te o in lavorazione.")
    pratiche_data = g_api.get_sheet_data('Pratiche')
    mie_pratiche = [p for p in pratiche_data if str(p.get('Email_Operatore', '')).lower() == str(email).lower()]
    
    if not mie_pratiche:
        st.info("Nessuna pratica assegnata al momento.")
    else:
        df = pd.DataFrame(mie_pratiche)
        st.dataframe(df[['ID_Pratica', 'Tipo', 'Stato_Attuale', 'Email_Richiedente']], use_container_width=True, hide_index=True)
        
        st.subheader("Gestione Rapida Pratica")
        pratica_selezionata = st.selectbox("Seleziona ID Pratica da gestire", [p['ID_Pratica'] for p in mie_pratiche])
        avanza_stato = st.selectbox("Avanza in Stato", ["In Lavorazione", "In attesa di riscontro (Sospesa)", "Conclusa"])
        
        if st.button("Aggiorna Stato"):
             update_pratica_stato(pratica_selezionata, avanza_stato)

def show_dispatcher_dashboard():
    st.write("Tutte le pratiche attive. Assegna le nuove pratiche agli Operatori.")
    
    # 1. Recupero Dati
    pratiche_data = g_api.get_sheet_data('Pratiche')
    utenti_data = g_api.get_sheet_data('Utenti')
    
    # 2. Filtraggio Operatori disponibili
    operatori = [u['Email'] for u in utenti_data if u.get('Ruolo_Sistema') in ['Worker', 'Dispatcher']]
    
    if not pratiche_data:
        st.info("Nessuna pratica presente a sistema.")
    else:
        df = pd.DataFrame(pratiche_data)
        st.dataframe(df[['ID_Pratica', 'Tipo', 'Stato_Attuale', 'Email_Operatore']], use_container_width=True, hide_index=True)
        
        st.subheader("Assegnazione Pratiche")
        with st.form("assegnazione_form"):
             col1, col2 = st.columns(2)
             with col1:
                  pratica_da_assegnare = st.selectbox("ID Pratica", [p['ID_Pratica'] for p in pratiche_data])
             with col2:
                  operatore_scelto = st.selectbox("Assegna a", operatori)
             
             submitted = st.form_submit_button("Conferma Assegnazione")
             if submitted:
                  update_pratica_operatore(pratica_da_assegnare, operatore_scelto)

def show_admin_dashboard():
    st.write("Pannello globale di supervisione.")
    # Come dispatcher, ma con più statistiche?
    st.info("Admin UI.")
