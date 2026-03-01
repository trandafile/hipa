import streamlit as st
import pandas as pd
import datetime
import json
from core.google_api import g_api

def calcola_sla(data_creazione_str, stato_attuale, tipo_pratica, conf_sla):
    try:
        if not data_creazione_str or stato_attuale in ['Conclusa', 'Archiviata']:
            return "N/D"
        
        data_c = datetime.datetime.fromisoformat(data_creazione_str)
        oggi = datetime.datetime.now()
        giorni_passati = (oggi - data_c).days
        
        sla_info = conf_sla.get(tipo_pratica)
        if not sla_info:
            return f"{giorni_passati} gg"
            
        sla_max = int(sla_info.get('SLA_Giorni', 15))
        warning = int(sla_info.get('Semaforo_Arancio', 10))
        critical = int(sla_info.get('Semaforo_Rosso', 14))
        
        colore = "🟢"
        if giorni_passati >= critical: colore = "🔴"
        elif giorni_passati >= warning: colore = "🟠"
        
        return f"{colore} {giorni_passati}/{sla_max} gg"
    except:
        return "-"

def update_pratica_operatore(id_pratica, email_op):
    data = g_api.get_sheet_data('Pratiche')
    row_idx = None
    for i, p in enumerate(data):
        if str(p.get('ID_Pratica')) == str(id_pratica):
            row_idx = i + 2
            break
    
    if row_idx:
        if g_api.update_cell('Pratiche', row_idx, 9, email_op):
            st.success(f"Pratica {id_pratica} assegnata a {email_op}")
            st.rerun()

def update_pratica_stato(id_pratica, nuovo_stato, nota=None, creds=None):
    pratiche_data = g_api.get_sheet_data('Pratiche')
    row_idx = None
    pratica_prev = None
    for i, p in enumerate(pratiche_data):
        if str(p.get('ID_Pratica')) == str(id_pratica):
            row_idx = i + 2
            pratica_prev = p
            break
            
    if row_idx:
        prev_stato = pratica_prev.get('Stato_Attuale')
        tp = pratica_prev.get('Tipo')
        
        g_api.update_cell('Pratiche', row_idx, 7, nuovo_stato)
        
        if nuovo_stato in ["Conclusa", "Archiviata"] and prev_stato not in ["Conclusa", "Archiviata"]:
            g_api.archive_pratica_folder(id_pratica, tp, user_creds_json=creds)
            
        elif nuovo_stato not in ["Conclusa", "Archiviata"] and prev_stato in ["Conclusa", "Archiviata"]:
            g_api.reopen_pratica_folder(id_pratica, tp, user_creds_json=creds)

        if nota:
            vecchia_nota = pratica_prev.get('Note_Condivise', '')
            nuova_nota = f"{vecchia_nota}\\n[{datetime.datetime.now().strftime('%d/%m %H:%M')}] {nota}"
            g_api.update_cell('Pratiche', row_idx, 10, nuova_nota)
            
            det_context = st.session_state.get('det_context', 'operatore')
            if det_context == 'richiedente':
                 g_api.update_cell('Pratiche', row_idx, 12, "Operatore")
            else:
                 user_email = str(st.session_state.get('user_email', '')).lower().strip()
                 req_email = str(pratica_prev.get('Email_Richiedente', '')).lower().strip()
                 if user_email != req_email:
                     g_api.update_cell('Pratiche', row_idx, 12, "Richiedente")
                 else:
                     g_api.update_cell('Pratiche', row_idx, 12, "")
        
        st_data = g_api.get_sheet_data('Storico_Fasi')
        g_api.append_row('Storico_Fasi', [len(st_data)+1, id_pratica, nuovo_stato, str(datetime.datetime.now()), "", nota or ""])
        st.success(f"Stato pratica {id_pratica} aggiornato!")
        st.rerun()

def approve_user(email, role):
    try:
        utenti_data = g_api.get_sheet_data('Utenti')
        row_idx = None
        for i, u in enumerate(utenti_data):
            if str(u.get('Email', '')).lower() == str(email).lower():
                row_idx = i + 2
                break
        
        if row_idx:
            g_api.update_cell('Utenti', row_idx, 8, role)
            g_api.update_cell('Utenti', row_idx, 9, 'Attivo')
            return True
        return False
    except Exception as e:
        st.error(f"Errore approvazione utente: {e}")
        return False

def reject_user(email):
    return g_api.delete_row_by_id('Utenti', 'Email', email)

def show_richiedente_dashboard(email):
    st.markdown("<style>div[data-testid='stHorizontalBlock'] { border-bottom: 1px solid #f0f0f0; padding-top: 10px; padding-bottom: 10px; border-radius: 4px; } div[data-testid='stHorizontalBlock']:nth-of-type(even) { background-color: #f9f9f0; } div[data-testid='stHorizontalBlock']:nth-of-type(odd) { background-color: #ffffff; } div[data-testid='stHorizontalBlock']:first-of-type { background-color: #eeeeee; font-weight: bold; }</style>", unsafe_allow_html=True)

    if 'dashboard_message' in st.session_state:
        st.success(st.session_state['dashboard_message'])
        del st.session_state['dashboard_message']

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Le tue pratiche")
    with col2:
        if st.button("➕ Nuova Pratica", use_container_width=True, type="primary"):
            st.session_state['current_page'] = "Nuova Pratica"
            st.rerun()
            
    pratiche_data = g_api.get_sheet_data('Pratiche')
    mie_pratiche_tutte = [p for p in pratiche_data if str(p.get('Email_Richiedente', '')).lower() == str(email).lower()]
    mie_pratiche = [p for p in mie_pratiche_tutte if p.get('Stato_Attuale') not in ['Conclusa', 'Archiviata']]
    mie_archiviate = [p for p in mie_pratiche_tutte if p.get('Stato_Attuale') in ['Conclusa', 'Archiviata']]
    
    conf_sla_raw = g_api.get_sheet_data('Configurazione_Pratiche')
    conf_sla = {c['Tipo']: c for c in conf_sla_raw}

    if not mie_pratiche:
        st.info("Non hai pratiche attive al momento. Clicca su 'Nuova Pratica' per iniziare.")
    else:
        c1, c1b, c2, c3, c4, c5 = st.columns([1.5, 2, 4, 1.5, 3, 1.5])
        c1.write("**ID**")
        c1b.write("**Progetto**")
        c2.write("**Titolo / Oggetto**")
        c3.write("**Data**")
        c4.write("**Stato e SLA**")
        c5.write("**Azione**")
        st.divider()
        for p in mie_pratiche:
            c1, c1b, c2, c3, c4, c5 = st.columns([1.5, 2, 4, 1.5, 3, 1.5])
            
            notif_val = str(p.get('Notifica_Nota', '')).strip()
            notif_html = "<span class='blink-icon'>✉️</span>" if notif_val == 'Richiedente' else ""
            c1.markdown(f"**{p['ID_Pratica']}**{notif_html}\\n\\n{p.get('Tipo', '')}", unsafe_allow_html=True)
            c1b.write(f"**{p.get('Progetto', 'N/D')}**")
            
            try:
                js = json.loads(p.get('JSON_Dati', '{}'))
                titolo = js.get('titolo', p.get('Oggetto', 'Senza Titolo'))
            except:
                titolo = p.get('Oggetto', 'Senza Titolo')
                
            c2.write(f"**{titolo}**\\n\\n_{str(p.get('Oggetto', ''))[:40]}..._")
            c3.write(str(p.get('Data_Creazione', ''))[:10])
            c4.write(f"*{p['Stato_Attuale']}*\\n\\n{calcola_sla(p.get('Data_Creazione', ''), p['Stato_Attuale'], p.get('Tipo'), conf_sla)}")
            with c5:
                if st.button("🔍", key=f"det_r_{p['ID_Pratica']}", help="Vedi Dettaglio"):
                    st.session_state['pratica_selezionata'] = p['ID_Pratica']
                    st.session_state['det_context'] = 'richiedente'
                    st.session_state['current_page'] = "Dettaglio Pratica"
                    st.rerun()

    if mie_archiviate:
        st.divider()
        with st.expander(f"📦 Pratiche Concluse / Archiviate ({len(mie_archiviate)})", expanded=False):
            for p in mie_archiviate:
                st.write(f"**{p['ID_Pratica']}** - {p.get('Oggetto', 'Senza Titolo')} ({p['Stato_Attuale']})")

def show_worker_dashboard(email):
    st.subheader("🛠️ Pannello Operatore (Carico di Lavoro)")
    pratiche_data = g_api.get_sheet_data('Pratiche')
    mie_assegnate_tutte = [p for p in pratiche_data if str(p.get('Email_Operatore', '')).lower() == str(email).lower()]
    mie_assegnate = [p for p in mie_assegnate_tutte if p.get('Stato_Attuale') not in ['Conclusa', 'Archiviata']]
    mie_concluse = [p for p in mie_assegnate_tutte if p.get('Stato_Attuale') in ['Conclusa', 'Archiviata']]

    if not mie_assegnate:
        st.info("Non hai pratiche in carico al momento.")
    else:
        for p in mie_assegnate:
            with st.container():
                c1, c2, c3 = st.columns([1, 4, 1])
                notif_val = str(p.get('Notifica_Nota', '')).strip()
                notif_html = "<span class='blink-icon'>✉️</span>" if notif_val == 'Operatore' else ""
                c1.markdown(f"**{p['ID_Pratica']}**{notif_html}", unsafe_allow_html=True)
                c2.write(f"**{p.get('Oggetto', 'N/D')}** - _Richiedente: {p['Email_Richiedente']}_")
                if c3.button("Lavora", key=f"work_{p['ID_Pratica']}", use_container_width=True):
                    st.session_state['pratica_selezionata'] = p['ID_Pratica']
                    st.session_state['det_context'] = 'operatore'
                    st.session_state['current_page'] = "Dettaglio Pratica"
                    st.rerun()

    if mie_concluse:
        st.divider()
        with st.expander("📦 Archivio Pratiche Concluse", expanded=False):
            for p in mie_concluse:
                st.write(f"**{p['ID_Pratica']}** - {p.get('Oggetto')} ({p['Stato_Attuale']})")

def show_dispatcher_dashboard():
    st.subheader("🚀 Pannello Smistamento (Dispatcher)")
    pratiche_data = g_api.get_sheet_data('Pratiche')
    utenti_data = g_api.get_sheet_data('Utenti')
    operatori = [u['Email'] for u in utenti_data if u.get('Ruolo_Sistema') in ['Worker', 'Dispatcher', 'Admin']]
    
    if not pratiche_data:
        st.info("Nessuna pratica a sistema.")
    else:
        df = pd.DataFrame(pratiche_data)
        st.dataframe(df[['ID_Pratica', 'Tipo', 'Progetto', 'Email_Richiedente', 'Stato_Attuale', 'Email_Operatore']], hide_index=True, use_container_width=True)
        
        st.subheader("🎯 Assegnazione Rapida")
        da_assegnare = [p['ID_Pratica'] for p in pratiche_data if not p.get('Email_Operatore')]
        if not da_assegnare:
            st.success("Tutte le pratiche sono assegnate.")
        else:
            with st.form("disp_form"):
                c1, c2 = st.columns(2)
                with c1: id_sel = st.selectbox("Pratica", da_assegnare)
                with c2: op_sel = st.selectbox("Operatore", operatori)
                if st.form_submit_button("Conferma", type="primary"):
                    update_pratica_operatore(id_sel, op_sel)

def show_admin_dashboard():
    st.subheader("🛡️ Pannello Supervisione (Admin)")
    
    pratiche_data = g_api.get_sheet_data('Pratiche')
    utenti_data = g_api.get_sheet_data('Utenti')
    
    conf_sla_raw = g_api.get_sheet_data('Configurazione_Pratiche')
    conf_sla = {c['Tipo']: c for c in conf_sla_raw}

    c1, c2, c3 = st.columns(3)
    c1.metric("Totale Pratiche", len(pratiche_data))
    c2.metric("Pratiche Chiuse", len([p for p in pratiche_data if p.get('Stato_Attuale') == 'Conclusa']))
    c3.metric("Utenti Registrati", len(utenti_data))
    
    st.divider()
    
    tab1, tab2 = st.tabs(["📋 Pratiche", "👤 Gestione Utenti"])
    
    with tab1:
        st.write("### Tutte le Pratiche")
        if not pratiche_data:
            st.info("Nessuna pratica presente.")
        else:
            c_h1, c_h1b, c_h2, c_h3, c_h4, c_h5 = st.columns([1.5, 2, 3, 2, 2, 1.5])
            c_h1.write("**ID / Tipo**")
            c_h1b.write("**Progetto**")
            c_h2.write("**Titolo / Richiedente**")
            c_h3.write("**Stato e SLA**")
            c_h4.write("**Operatore**")
            c_h5.write("**Azione**")
            st.divider()
            for p in pratiche_data:
                c1, c1b, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 2, 2, 1.5])
                
                notif_val = str(p.get('Notifica_Nota', '')).strip()
                notif_html = "<span class='blink-icon'>✉️</span>" if notif_val == 'Operatore' else ""
                c1.markdown(f"**{p['ID_Pratica']}**{notif_html}\\n\\n{p['Tipo']}", unsafe_allow_html=True)
                c1b.write(f"**{p.get('Progetto', 'N/D')}**")
                
                try:
                    js = json.loads(p.get('JSON_Dati', '{}'))
                    titolo = js.get('titolo', p.get('Oggetto', 'Senza Titolo'))
                except:
                    titolo = p.get('Oggetto', 'Senza Titolo')
                
                c2.write(f"**{titolo}**\\n\\n_{str(p.get('Email_Richiedente', '')).split('@')[0]}_")
                c3.write(f"*{p['Stato_Attuale']}*\\n\\n{calcola_sla(p.get('Data_Creazione', ''), p['Stato_Attuale'], p.get('Tipo'), conf_sla)}")
                c4.write(str(p.get('Email_Operatore', '')).split('@')[0] if p.get('Email_Operatore') else "-")
                with c5:
                    if st.button("🔍 Dettagli", key=f"det_a_{p['ID_Pratica']}", help="Vedi Dettaglio Pratica"):
                        st.session_state['pratica_selezionata'] = p['ID_Pratica']
                        st.session_state['det_context'] = 'admin'
                        st.session_state['current_page'] = "Dettaglio Pratica"
                        st.rerun()
                st.divider()

        st.subheader("🎯 Assegnazione / Cambio Operatore")
        operatori = [u['Email'] for u in utenti_data if u.get('Ruolo_Sistema') in ['Worker', 'Dispatcher', 'Admin']]
        ids_pratiche = [p['ID_Pratica'] for p in pratiche_data]
        if ids_pratiche:
            with st.form("admin_assignment_form"):
                col_p, col_o = st.columns(2)
                with col_p: id_p = st.selectbox("Seleziona ID Pratica", ids_pratiche)
                with col_o: email_o = st.selectbox("Assegna a Operatore", operatori)
                if st.form_submit_button("Conferma Assegnazione", type="primary"):
                    update_pratica_operatore(id_p, email_o)

    with tab2:
        st.subheader("👤 Gestione Utenti e Approvazioni")
        pending_users = [u for u in utenti_data if u.get('Stato') == 'In Attesa']
        
        if not pending_users:
            st.success("Non ci sono richieste di accesso in attesa.")
        else:
            st.warning(f"Hai {len(pending_users)} richieste da approvare.")
            for u in pending_users:
                with st.expander(f"Richiesta da: {u['Nome']} {u['Cognome']} ({u['Email']})"):
                    col_u1, col_u2 = st.columns(2)
                    col_u1.write(f"**Ruolo Accademico:** {u.get('Ruolo_Accademico')}")
                    col_u1.write(f"**Data Nascita:** {u.get('Data_Nascita')}")
                    nuovo_ruolo = col_u2.selectbox("Assegna Ruolo Sistema", ["Richiedente", "Worker", "Dispatcher", "Admin"], key=f"role_{u['Email']}")
                    
                    cl1, cl2 = col_u2.columns(2)
                    if cl1.button("✅ Approva", key=f"app_{u['Email']}", type="primary", use_container_width=True):
                        if approve_user(u['Email'], nuovo_ruolo): st.rerun()
                    if cl2.button("❌ Rifiuta", key=f"rej_{u['Email']}", use_container_width=True):
                        if reject_user(u['Email']): st.rerun()
        
        st.divider()
        st.write("### Tutti gli Utenti")
        df_utenti = pd.DataFrame(utenti_data)
        st.dataframe(df_utenti[['Email', 'Nome', 'Cognome', 'Ruolo_Sistema', 'Stato']], hide_index=True, use_container_width=True)

    st.divider()
    st.subheader("🤖 Assegnazione Automatica")
    impostazioni = g_api.get_sheet_data('Impostazioni_Sistema')
    tipologie = ["Acquisto", "Contratti"]
    col_t1, col_t2 = st.columns(2)
    for idx, tipo in enumerate(tipologie):
        chiave_impostazione = f"AutoAssign_{tipo}"
        valore_attuale = next((i['Valore'] for i in impostazioni if i['Chiave'] == chiave_impostazione), "[]")
        target_col = col_t1 if idx % 2 == 0 else col_t2
        with target_col:
             with st.form(f"f_auto_{tipo}"):
                 ops_selezionati = st.multiselect(f"Operatori '{tipo}'", operatori, default=json.loads(valore_attuale) if valore_attuale.startswith('[') else [])
                 if st.form_submit_button("Salva"):
                     g_api.append_row('Impostazioni_Sistema', [chiave_impostazione, json.dumps(ops_selezionati)])
                     st.rerun()

def show_home_dashboard():
    st.title("Piattaforma HipA")
    st.write("Benvenuto nel Sistema di Ticketing Amministrativo Universitario.")
    
    email = st.session_state.get('user_email')
    pratiche_data = g_api.get_sheet_data('Pratiche')
    mie_pratiche = [p for p in pratiche_data if str(p.get('Email_Richiedente', '')).lower() == str(email).lower()]
    notifiche_richiedente = len([p for p in mie_pratiche if str(p.get('Notifica_Nota', '')).strip() == 'Richiedente'])

    c1, c2, c3 = st.columns(3)
    c1.metric("Le tue Pratiche Totali", len(mie_pratiche))
    c2.metric("Pratiche Attive", len([p for p in mie_pratiche if p.get('Stato_Attuale') not in ['Conclusa', 'Archiviata']]))
    if notifiche_richiedente > 0:
        c3.metric("Nuove Note ✉️", notifiche_richiedente, delta="Nuovo!")
    else:
        c3.metric("Nuove Note", 0)

    st.markdown("---")
    ca1, ca2 = st.columns(2)
    with ca1:
        if st.button("📋 Vai alle mie Pratiche", use_container_width=True):
            st.session_state['current_page'] = "Pannello Richiedente"; st.rerun()
    with ca2:
        if st.button("➕ Invia Nuova Richiesta", use_container_width=True, type="primary"):
            st.session_state['current_page'] = "Nuova Pratica"; st.rerun()

    ruolo = str(st.session_state.get('user_role', '')).lower()
    if ruolo == 'admin':
        st.info("Hai accesso come Amministratore. [Vai al Pannello Admin]")
        if st.button("🔍 Pannello Admin"): st.session_state['current_page'] = "Pannello Admin"; st.rerun()
    elif ruolo in ['worker', 'dispatcher']:
        st.info("Benvenuto Operatore. [Vai al tuo Pannello]")
        if st.button("🔍 Pannello Operatore"): st.session_state['current_page'] = "Pannello Operatore"; st.rerun()
