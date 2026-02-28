import streamlit as st
import pandas as pd
import datetime
import json
from core.google_api import g_api

def calcola_sla(data_str, stato, tipo, configs=None):
    if stato in ['Conclusa', 'Archiviata']:
        return "⚪ Chiusa/Arch."
    
    # Default (giorni totali per scadere e giorni dopo cui diventa arancione)
    sla_giorni = 30   # rossa dopo questo numero di giorni trascorsi
    s_arancio = 20    # arancione dopo questo numero di giorni trascorsi
    
    if configs and tipo in configs:
        conf = configs[tipo]
        try:
            sla_giorni = int(conf.get('SLA_Giorni', 30))
            s_arancio = int(conf.get('Semaforo_Arancio', int(sla_giorni * 0.7)))
        except:
            pass

    try:
        data_str = str(data_str).strip()
        dt = None
        for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
            try:
                dt = datetime.datetime.strptime(data_str, fmt)
                break
            except:
                continue
        if not dt:
            return "🟢 In regola (0gg)"
    except:
        return "🟢 In regola (0gg)"
    
    giorni_trascorsi = (datetime.datetime.now() - dt).days
    giorni_rimanenti = max(0, sla_giorni - giorni_trascorsi)
    
    if giorni_trascorsi >= sla_giorni:
        return f"🔴 Scaduta ({giorni_trascorsi - sla_giorni}gg oltre)"
    elif giorni_trascorsi >= s_arancio:
        return f"🟠 In Scadenza ({giorni_rimanenti}gg rim.)"
    else:
        return f"🟢 In regola ({giorni_rimanenti}gg rim.)"

def autoassegna_operatore(tipo):
    impostazioni = g_api.get_sheet_data('Impostazioni_Sistema')
    chiave = f"AutoAssign_{tipo}"
    valore = next((i['Valore'] for i in impostazioni if i['Chiave'] == chiave), "[]")
    try:
        operatori_candidati = json.loads(valore)
    except:
        operatori_candidati = []
        
    if not operatori_candidati:
        return "" # Nessuna regola, assegnazione manuale
        
    pratiche = g_api.get_sheet_data('Pratiche')
    carichi = {op: 0 for op in operatori_candidati}
    for p in pratiche:
        op = p.get('Email_Operatore')
        stato = p.get('Stato_Attuale')
        if op in carichi and stato not in ['Conclusa', 'Archiviata']:
            carichi[op] += 1
            
    # Ritorna l'operatore col carico minore
    return min(carichi, key=carichi.get)

def show_dashboard():
    st.header("🗂️ Cruscotto Pratiche")
    
    # --- Fix Header Silente (una tantum per sessione) ---
    if 'header_fixed' not in st.session_state:
        try:
            # Recuperiamo il foglio direttamente per controllare le intestazioni
            sheet = g_api.doc.worksheet('Pratiche')
            headers = sheet.row_values(1)
            # Notifica_Nota è la colonna 11
            if len(headers) < 11 or "Notifica_Nota" not in headers:
                sheet.update_cell(1, 11, "Notifica_Nota")
            st.session_state['header_fixed'] = True
        except:
            pass

    role = st.session_state.get('user_role', 'Richiedente')
    email = st.session_state.get('user_email', '')
    
    if role == 'Richiedente':
         show_richiedente_dashboard(email)
    elif role == 'Worker':
         show_worker_dashboard(email)
    elif role == 'Dispatcher':
         show_dispatcher_dashboard()
    elif role == 'Admin':
         # L'Admin vede il pannello di supervisione
         show_admin_dashboard()
    else:
         st.error(f"Ruolo sconosciuto: {role}")

def update_pratica_operatore(id_pratica, new_operator_email):
    """Aggiorna l'operatore assegnato a una pratica nel DB"""
    pratiche_data = g_api.get_sheet_data('Pratiche')
    row_idx = None
    for i, row in enumerate(pratiche_data):
        if str(row.get('ID_Pratica')) == str(id_pratica):
            row_idx = i + 2 # +1 header, +1 shift
            break
            
    if row_idx:
        # Colonna 8 è 'Email_Operatore' nel nostro schema REQUIRED_SHEETS
        success = g_api.update_cell('Pratiche', row_idx, 8, new_operator_email)
        if success:
             # Impostiamo lo stato iniziale richiesto dall'utente
             g_api.update_cell('Pratiche', row_idx, 6, "Non preso in carico")
             st.success(f"Pratica {id_pratica} assegnata a {new_operator_email} (Stato: Non preso in carico)")
             st.rerun()
    else:
        st.error("Pratica non trovata.")

def update_pratica_stato(id_pratica, nuovo_stato, nota=""):
    """Aggiorna lo stato di una pratica e opzionalmente aggiunge una nota condivisa"""
    pratiche_data = g_api.get_sheet_data('Pratiche')
    row_idx = None
    for i, row in enumerate(pratiche_data):
        if str(row.get('ID_Pratica')) == str(id_pratica):
            row_idx = i + 2
            break
            
    if row_idx:
        pratica_prev = pratiche_data[row_idx-2]
        prev_stato = pratica_prev.get('Stato_Attuale')
        
        # Colonna 6 è 'Stato_Attuale', Colonna 9 è 'Note_Condivise', Colonna 11 è 'Notifica_Nota'
        g_api.update_cell('Pratiche', row_idx, 6, nuovo_stato)
        
        # Gestione Folders su Drive
        tp = pratica_prev.get('Tipo', 'Acquisti')
        creds = st.session_state.get('user_creds')
        
        # Se passa ad un archivio da uno stato attivo
        if nuovo_stato in ["Conclusa", "Archiviata"] and prev_stato not in ["Conclusa", "Archiviata"]:
            g_api.archive_pratica_folder(id_pratica, tp, user_creds_json=creds)
            
        # Se viene riaperta da un archivio
        elif nuovo_stato not in ["Conclusa", "Archiviata"] and prev_stato in ["Conclusa", "Archiviata"]:
            g_api.reopen_pratica_folder(id_pratica, tp, user_creds_json=creds)

        if nota:
            # Recuperiamo la vecchia nota per fare l'append
            vecchia_nota = pratica_prev.get('Note_Condivise', '')
            nuova_nota = f"{vecchia_nota}\n[{datetime.datetime.now().strftime('%d/%m %H:%M')}] {nota}"
            g_api.update_cell('Pratiche', row_idx, 9, nuova_nota)
            
            # Determina a chi va la notifica in base al contesto
            det_context = st.session_state.get('det_context', 'operatore') # Default operatore qui perché è il pannello worker
            
            if det_context == 'richiedente':
                 g_api.update_cell('Pratiche', row_idx, 11, "Operatore")
            else:
                 # Se l'operatore non è il richiedente, notifica il richiedente
                 user_email = str(st.session_state.get('user_email', '')).lower().strip()
                 req_email = str(pratiche_data[row_idx-2].get('Email_Richiedente', '')).lower().strip()
                 if user_email != req_email:
                     g_api.update_cell('Pratiche', row_idx, 11, "Richiedente")
                 else:
                     g_api.update_cell('Pratiche', row_idx, 11, "")
        
        # Aggiungiamo anche una riga allo Storico_Fasi
        data_ora = str(datetime.datetime.now())
        g_api.append_row('Storico_Fasi', [len(g_api.get_sheet_data('Storico_Fasi'))+1, id_pratica, nuovo_stato, data_ora, "", nota])
        
        st.success(f"Stato pratica {id_pratica} aggiornato!")
        st.rerun()

def show_richiedente_dashboard(email):
    # CSS per righe alternate e stile tabella
    st.markdown("""
        <style>
        /* Container delle righe (horizontal blocks) */
        div[data-testid="stHorizontalBlock"] {
            border-bottom: 1px solid #f0f0f0;
            padding-top: 10px;
            padding-bottom: 10px;
            border-radius: 4px;
        }
        /* Righe alternate: Grigio giallino chiaro */
        div[data-testid="stHorizontalBlock"]:nth-of-type(even) {
            background-color: #f9f9f0;
        }
        /* Righe alternate: Bianco */
        div[data-testid="stHorizontalBlock"]:nth-of-type(odd) {
            background-color: #ffffff;
        }
        /* Header della tabella (il primo dopo il titolo) */
        div[data-testid="stHorizontalBlock"]:first-of-type {
            background-color: #eeeeee;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

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
    
    # Separazione pratiche attive e archiviate/concluse
    mie_pratiche = [p for p in mie_pratiche_tutte if p.get('Stato_Attuale') not in ['Conclusa', 'Archiviata']]
    mie_archiviate = [p for p in mie_pratiche_tutte if p.get('Stato_Attuale') in ['Conclusa', 'Archiviata']]
    
    conf_sla_raw = g_api.get_sheet_data('Configurazione_Pratiche')
    conf_sla = {c['Tipo']: c for c in conf_sla_raw}

    if not mie_pratiche:
        st.info("Non hai pratiche attive al momento. Clicca su 'Nuova Pratica' per iniziare.")
    else:
        c1, c1b, c2, c3, c4, c5 = st.columns([1.5, 2, 4, 2, 3, 1.5])
        c1.write("**ID**")
        c1b.write("**Progetto**")
        c2.write("**Titolo / Oggetto**")
        c3.write("**Data**")
        c4.write("**Stato e SLA**")
        c5.write("**Azione**")
        st.divider()
        for p in mie_pratiche:
            c1, c1b, c2, c3, c4, c5 = st.columns([1.5, 2, 4, 2, 3, 1.5])
            
            notif_val = str(p.get('Notifica_Nota', '')).strip()
            notif_html = "<span class='blink-icon'>✉️</span>" if notif_val == 'Richiedente' else ""
            c1.markdown(f"**{p['ID_Pratica']}**{notif_html}\n\n{p.get('Tipo', '')}", unsafe_allow_html=True)
            c1b.write(f"**{p.get('Progetto', 'N/D')}**")
            
            try:
                js = json.loads(p.get('JSON_Dati', '{}'))
                titolo = js.get('titolo', p.get('Oggetto', 'Senza Titolo'))
            except:
                titolo = p.get('Oggetto', 'Senza Titolo')
                
            c2.write(f"**{titolo}**\n\n_{str(p.get('Oggetto', ''))[:40]}..._")
            c3.write(str(p.get('Data_Creazione', ''))[:10])
            c4.write(f"*{p['Stato_Attuale']}*\n\n{calcola_sla(p.get('Data_Creazione', ''), p['Stato_Attuale'], p.get('Tipo'), conf_sla)}")
            with c5:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🔍", key=f"det_r_{p['ID_Pratica']}", help="Vedi Dettaglio"):
                        st.session_state['pratica_selezionata'] = p['ID_Pratica']
                        st.session_state['det_context'] = 'richiedente'
                        st.session_state['current_page'] = "Dettaglio Pratica"
                        st.rerun()
                if p['Stato_Attuale'] in ['Nuova Inserita', 'Non preso in carico']:
                     with col_btn2:
                         if st.button("❌", key=f"del_r_{p['ID_Pratica']}", help="Elimina Pratica (Non ancora presa in carico)"):
                             if g_api.delete_row_by_id('Pratiche', 'ID_Pratica', p['ID_Pratica']):
                                  st.session_state['dashboard_message'] = "Pratica eliminata con successo."
                                  st.rerun()

    # --- Sezione Pratiche Archiviate / Concluse ---
    if mie_archiviate:
        st.divider()
        with st.expander(f"📦 Pratiche Concluse / Archiviate ({len(mie_archiviate)})", expanded=False):
            ca1, ca1b, ca2, ca3, ca4, ca5 = st.columns([1.5, 2, 4, 2, 3, 1.5])
            ca1.write("**ID**")
            ca1b.write("**Progetto**")
            ca2.write("**Titolo / Oggetto**")
            ca3.write("**Data**")
            ca4.write("**Stato**")
            ca5.write("**Azione**")
            st.divider()
            for p in mie_archiviate:
                ca1, ca1b, ca2, ca3, ca4, ca5 = st.columns([1.5, 2, 4, 2, 3, 1.5])
                ca1.write(f"**{p['ID_Pratica']}**\n\n{p.get('Tipo', '')}")
                ca1b.write(f"**{p.get('Progetto', 'N/D')}**")
                try:
                    js = json.loads(p.get('JSON_Dati', '{}'))
                    titolo = js.get('titolo', p.get('Oggetto', 'Senza Titolo'))
                except:
                    titolo = p.get('Oggetto', 'Senza Titolo')
                ca2.write(f"**{titolo}**\n\n_{str(p.get('Oggetto', ''))[:40]}..._")
                ca3.write(str(p.get('Data_Creazione', ''))[:10])
                ca4.write(f"*{p['Stato_Attuale']}*")
                with ca5:
                    if st.button("🔍", key=f"det_arch_{p['ID_Pratica']}", help="Vedi Dettaglio"):
                        st.session_state['pratica_selezionata'] = p['ID_Pratica']
                        st.session_state['current_page'] = "Dettaglio Pratica"
                        st.rerun()

def show_worker_dashboard(email):
    # CSS per righe alternate (già definito sopra, ma iniettiamo per sicurezza o coerenza)
    st.markdown("""
        <style>
        div[data-testid="stHorizontalBlock"] { padding: 8px; border-radius: 4px; margin-bottom: 2px; }
        div[data-testid="stHorizontalBlock"]:nth-of-type(even) { background-color: #f9f9f0; }
        div[data-testid="stHorizontalBlock"]:first-of-type { background-color: #eeeeee; }
        </style>
    """, unsafe_allow_html=True)
    
    pratiche_data = g_api.get_sheet_data('Pratiche')
    mie_pratiche = [p for p in pratiche_data if str(p.get('Email_Operatore', '')).lower() == str(email).lower()]
    
    conf_sla_raw = g_api.get_sheet_data('Configurazione_Pratiche')
    conf_sla = {c['Tipo']: c for c in conf_sla_raw}

    if not mie_pratiche:
        st.info("Nessuna pratica assegnata al momento.")
    else:
        c1, c1b, c2, c3, c4 = st.columns([1.5, 2, 4, 3, 1.5])
        c1.write("**ID**")
        c1b.write("**Progetto**")
        c2.write("**Titolo / Richiedente**")
        c3.write("**Stato e SLA**")
        c4.write("**Azioni**")
        st.divider()
        for p in mie_pratiche:
            c1, c1b, c2, c3, c4 = st.columns([1.5, 2, 4, 3, 1.5])
            
            notif_val = str(p.get('Notifica_Nota', '')).strip()
            notif_html = "<span class='blink-icon'>✉️</span>" if notif_val == 'Operatore' else ""
            c1.markdown(f"**{p['ID_Pratica']}**{notif_html}\n\n{p.get('Tipo', '')}", unsafe_allow_html=True)
            c1b.write(f"**{p.get('Progetto', 'N/D')}**")
            
            try:
                js = json.loads(p.get('JSON_Dati', '{}'))
                titolo = js.get('titolo', p.get('Oggetto', 'Senza Titolo'))
            except:
                titolo = p.get('Oggetto', 'Senza Titolo')
                
            c2.write(f"**{titolo}**\n_{str(p.get('Email_Richiedente', '')).split('@')[0]}_")
            c3.write(f"*{p['Stato_Attuale']}*\n\n{calcola_sla(p.get('Data_Creazione', ''), p['Stato_Attuale'], p.get('Tipo'), conf_sla)}")
            with c4:
                if st.button("🔍 Lavora", key=f"det_w_{p['ID_Pratica']}", help="Vedi Dettaglio e Aggiorna Stato"):
                    st.session_state['pratica_selezionata'] = p['ID_Pratica']
                    st.session_state['det_context'] = 'operatore'
                    st.session_state['current_page'] = "Dettaglio Pratica"
                    st.rerun()
        
        st.divider()
        st.subheader("📝 Gestione Pratica")
        with st.form("gestione_worker"):
            id_p = st.selectbox("Seleziona ID", [p['ID_Pratica'] for p in mie_pratiche])
            
            # Determina le fasi in base al tipo di pratica selezionata
            tipo_sel = next((p['Tipo'] for p in mie_pratiche if p['ID_Pratica'] == id_p), "Acquisto")
            
            if tipo_sel == "Acquisto":
                 stati_possibili = [
                     "Non preso in carico",
                     "Fase 1: verifica documentazione",
                     "Fase 2: ordine trasmesso al fornitore",
                     "In attesa di riscontri",
                     "Conclusa"
                 ]
            else:
                 stati_possibili = ["In Lavorazione", "In attesa di riscontri", "Conclusa"]
            
            nuovo_s = st.selectbox("Avanzamento Fasi / Stato", stati_possibili)
            nota = st.text_area("Aggiungi Nota (visibile al richiedente)")
            if st.form_submit_button("Salva Aggiornamento", type="primary"):
                update_pratica_stato(id_p, nuovo_s, nota)

        # --- Archivio Pratiche per Operatore ---
        mie_archiviate = [p for p in pratiche_data if str(p.get('Email_Operatore', '')).lower() == str(email).lower() and p.get('Stato_Attuale') in ['Conclusa', 'Archiviata']]
        if mie_archiviate:
            st.divider()
            with st.expander(f"📦 Archivio Pratiche Concluse ({len(mie_archiviate)})", expanded=False):
                ca1, ca1b, ca2, ca3, ca4 = st.columns([1.5, 2, 4, 3, 1.5])
                ca1.write("**ID**")
                ca1b.write("**Progetto**")
                ca2.write("**Titolo / Richiedente**")
                ca3.write("**Stato**")
                ca4.write("**Azioni**")
                st.divider()
                for p in mie_archiviate:
                    ca1, ca1b, ca2, ca3, ca4 = st.columns([1.5, 2, 4, 3, 1.5])
                    ca1.write(f"**{p['ID_Pratica']}**\n\n{p.get('Tipo', '')}")
                    ca1b.write(f"**{p.get('Progetto', 'N/D')}**")
                    try:
                        js = json.loads(p.get('JSON_Dati', '{}'))
                        titolo = js.get('titolo', p.get('Oggetto', 'Senza Titolo'))
                    except:
                        titolo = p.get('Oggetto', 'Senza Titolo')
                    ca2.write(f"**{titolo}**\n_{str(p.get('Email_Richiedente', '')).split('@')[0]}_")
                    ca3.write(f"*{p['Stato_Attuale']}*")
                    with ca4:
                        if st.button("🔍 Vedi", key=f"det_arch_w_{p['ID_Pratica']}", help="Vedi Dettaglio"):
                            st.session_state['pratica_selezionata'] = p['ID_Pratica']
                            st.session_state['det_context'] = 'operatore'
                            st.session_state['current_page'] = "Dettaglio Pratica"
                            st.rerun()

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
    st.write("### Tutte le Pratiche")
    if not pratiche_data:
         st.info("Nessuna pratica presente.")
    else:
        c1, c1b, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 2, 2, 1.5])
        c1.write("**ID / Tipo**")
        c1b.write("**Progetto**")
        c2.write("**Titolo / Richiedente**")
        c3.write("**Stato e SLA**")
        c4.write("**Operatore**")
        c5.write("**Azione**")
        st.divider()
        for p in pratiche_data:
            c1, c1b, c2, c3, c4, c5 = st.columns([1.5, 2, 3, 2, 2, 1.5])
            
            notif_val = str(p.get('Notifica_Nota', '')).strip()
            notif_html = "<span class='blink-icon'>✉️</span>" if notif_val == 'Operatore' else ""
            c1.markdown(f"**{p['ID_Pratica']}**{notif_html}\n{p['Tipo']}", unsafe_allow_html=True)
            c1b.write(f"**{p.get('Progetto', 'N/D')}**")
            
            try:
                js = json.loads(p.get('JSON_Dati', '{}'))
                titolo = js.get('titolo', p.get('Oggetto', 'Senza Titolo'))
            except:
                titolo = p.get('Oggetto', 'Senza Titolo')
                
            c2.write(f"**{titolo}**\n_{str(p.get('Email_Richiedente', '')).split('@')[0]}_")
            c3.write(f"*{p['Stato_Attuale']}*\n\n{calcola_sla(p.get('Data_Creazione', ''), p['Stato_Attuale'], p.get('Tipo'), conf_sla)}")
            c4.write(str(p.get('Email_Operatore', '')).split('@')[0] if p.get('Email_Operatore') else "-")
            with c5:
                if st.button("🔍 Dettagli", key=f"det_a_{p['ID_Pratica']}", help="Vedi Dettaglio Pratica"):
                    st.session_state['pratica_selezionata'] = p['ID_Pratica']
                    st.session_state['det_context'] = 'operatore'
                    st.session_state['current_page'] = "Dettaglio Pratica"
                    st.rerun()
    
    st.write("### Gestione Utenti")
    if utenti_data:
        st.dataframe(pd.DataFrame(utenti_data), use_container_width=True, hide_index=True)
        
    st.divider()
    st.subheader("🎯 Assegnazione / Cambio Operatore")
    st.write("Usa questo modulo per assegnare una pratica a un operatore o cambiare l'assegnazione attuale.")
    
    operatori = [u['Email'] for u in utenti_data if u.get('Ruolo_Sistema') in ['Worker', 'Dispatcher', 'Admin']]
    ids_pratiche = [p['ID_Pratica'] for p in pratiche_data]
    
    if ids_pratiche:
        with st.form("admin_assignment_form"):
            col_p, col_o = st.columns(2)
            with col_p:
                id_p = st.selectbox("Seleziona ID Pratica", ids_pratiche)
            with col_o:
                email_o = st.selectbox("Assegna a Operatore", operatori)
            
            if st.form_submit_button("Conferma Assegnazione", type="primary"):
                update_pratica_operatore(id_p, email_o)
    else:
        st.info("Nessuna pratica da assegnare.")

    st.divider()
    st.subheader("🤖 Assegnazione Automatica (Regole di Smistamento)")
    st.write("Configura gli operatori predefiniti per tipologia di pratica. Il sistema assegerà le nuove pratiche all'operatore col carico minore tra quelli selezionati.")
    
    impostazioni = g_api.get_sheet_data('Impostazioni_Sistema')
    tipologie = ["Acquisto", "Contratti"]
    
    col_t1, col_t2 = st.columns(2)
    for idx, tipo in enumerate(tipologie):
        chiave_impostazione = f"AutoAssign_{tipo}"
        valore_attuale = next((i['Valore'] for i in impostazioni if i['Chiave'] == chiave_impostazione), "[]")
        try:
             ops_attuali = json.loads(valore_attuale)
        except:
             ops_attuali = []
             
        target_col = col_t1 if idx % 2 == 0 else col_t2
        with target_col:
             with st.form(f"form_autoassign_{tipo}"):
                 ops_selezionati = st.multiselect(
                     f"Operatori per '{tipo}'", 
                     operatori, 
                     default=[op for op in ops_attuali if op in operatori]
                 )
                 if st.form_submit_button("Salva Regola"):
                     row_idx = None
                     for i_idx, imp in enumerate(impostazioni):
                         if imp['Chiave'] == chiave_impostazione:
                             row_idx = i_idx + 2
                             break
                     
                     nuovo_valore = json.dumps(ops_selezionati)
                     if row_idx:
                         g_api.update_cell('Impostazioni_Sistema', row_idx, 2, nuovo_valore)
                     else:
                         g_api.append_row('Impostazioni_Sistema', [chiave_impostazione, nuovo_valore])
                     st.session_state['dashboard_message'] = f"Regola per {tipo} aggiornata."
                     st.rerun()

    st.divider()
    st.subheader("⏱️ Configurazione Tempi di Lavorazione (SLA)")
    st.write("Definisci i giorni attesi per tipologia e le soglie per il cambio colore.")
    st.info("ℹ️ **Soglia Arancio**: Numero di **giorni trascorsi** dopo i quali la pratica diventa arancione. Es: se imposti 5, dopo 5 giorni dalla sottomissione diventa arancione. Imposta 0 = diventa subito arancione.")
    
    conf_sla_data = g_api.get_sheet_data('Configurazione_Pratiche')
    
    # Mostra i valori attuali memorizzati
    if conf_sla_data:
        st.write("**Valori attuali in database:**")
        df_conf = pd.DataFrame(conf_sla_data)[['Tipo', 'SLA_Giorni', 'Semaforo_Arancio']]
        st.dataframe(df_conf, use_container_width=True, hide_index=True)
    
    col_s1, col_s2 = st.columns(2)
    for idx, tipo in enumerate(tipologie):
        conf_attuale = next((c for c in conf_sla_data if c['Tipo'] == tipo), None)
        
        target_col = col_s1 if idx % 2 == 0 else col_s2
        with target_col:
             with st.form(f"form_sla_{tipo}"):
                 st.write(f"**Tipologia: {tipo}**")
                 days = st.number_input("Giorni Totali (SLA)", min_value=1, value=int(conf_attuale['SLA_Giorni']) if conf_attuale else 30)
                 warn = st.number_input("Soglia Arancio (Giorni trascorsi)", min_value=0, value=int(conf_attuale['Semaforo_Arancio']) if conf_attuale else 20, help="Dopo quanti giorni dalla sottomissione la pratica diventa arancione.")
                 
                 if st.form_submit_button(f"Salva SLA {tipo}"):
                     # Strategia: elimina tutte le righe per questo tipo, poi reinserisci
                     sheet_data_fresh = g_api.get_sheet_data('Configurazione_Pratiche')
                     # Trova e cancella tutte le righe duplicate per questo tipo (dal fondo)
                     rows_to_delete = []
                     for i_idx, c in enumerate(sheet_data_fresh):
                         if str(c.get('Tipo', '')).strip() == str(tipo).strip():
                             rows_to_delete.append(i_idx + 2)  # 1-indexed, +1 header
                     
                     # Elimina in ordine inverso per non alterare gli indici
                     if rows_to_delete:
                         try:
                             sheet_obj = g_api.doc.worksheet('Configurazione_Pratiche')
                             for row_i in sorted(rows_to_delete, reverse=True):
                                 sheet_obj.delete_rows(row_i)
                         except Exception as e:
                             st.warning(f"Errore eliminazione vecchie righe: {e}")
                     
                     # Reinserisci con i valori aggiornati
                     g_api.append_row('Configurazione_Pratiche', [tipo, days, warn, 0])
                     
                     st.session_state['dashboard_message'] = f"SLA per {tipo} aggiornata ({days}gg, soglia arancio: {warn}gg)."
                     st.cache_data.clear()
                     st.rerun()

def show_home_dashboard():
    """Pagina di atterraggio generale con statistiche e benvenuto"""
    st.subheader(f"👋 Benvenuto, {st.session_state.get('user_given_name', 'Utente')}!")
    
    email = st.session_state.get('user_email', '')
    pratiche_data = g_api.get_sheet_data('Pratiche')
    mie_pratiche = [p for p in pratiche_data if str(p.get('Email_Richiedente', '')).lower() == str(email).lower()]
    
    # Notifiche pendenti per il richiedente
    notifiche_richiedente = len([p for p in mie_pratiche if str(p.get('Notifica_Nota', '')).strip() == 'Richiedente'])
    
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Le tue Pratiche Totali", len(mie_pratiche))
    with c2:
        pratiche_attive = len([p for p in mie_pratiche if p.get('Stato_Attuale') not in ['Conclusa', 'Archiviata']])
        st.metric("Pratiche in Lavorazione", pratiche_attive)
    with c3:
        if notifiche_richiedente > 0:
            st.metric("Nuove Note da Leggere ✉️", notifiche_richiedente, delta="Nuovo!")
        else:
            st.metric("Nuove Note da Leggere", 0)

    st.markdown("---")
    
    col_info, col_notif = st.columns([2, 1])
    
    with col_info:
        st.write("### 🚀 Accesso Rapido")
        st.info("Utilizza il menu a sinistra per navigare tra le sezioni del portale.")
        
        ca1, ca2 = st.columns(2)
        with ca1:
            if st.button("📋 Vai alle mie Pratiche", use_container_width=True):
                st.session_state['current_page'] = "Pannello Richiedente"
                st.rerun()
        with ca2:
            if st.button("➕ Invia Nuova Richiesta", use_container_width=True, type="primary"):
                st.session_state['current_page'] = "Nuova Pratica"
                st.rerun()
    
    with col_notif:
        if notifiche_richiedente > 0:
            st.warning(f"Hai **{notifiche_richiedente}** pratiche con nuove comunicazioni non lette. Controllale nel tuo pannello.")
        else:
            st.success("Non ci sono nuove comunicazioni per te.")
            
    # --- Sezioni Specifiche per Ruolo ---
    ruolo = str(st.session_state.get('user_role', '')).lower()
    
    if ruolo == 'admin':
        st.markdown("---")
        st.write("### 🛡️ Supervisione Sistema (Admin)")
        utenti_data = g_api.get_sheet_data('Utenti')
        
        ca1, ca2, ca3 = st.columns(3)
        ca1.metric("Totale Pratiche Sistema", len(pratiche_data))
        ca2.metric("Pratiche Chiuse", len([p for p in pratiche_data if p.get('Stato_Attuale') == 'Conclusa']))
        ca3.metric("Utenti Registrati", len(utenti_data))
        
        if st.button("🔍 Vai al Pannello Admin", use_container_width=True):
            st.session_state['current_page'] = "Pannello Admin"
            st.rerun()

    elif ruolo in ['worker', 'dispatcher']:
        st.markdown("---")
        st.write("### 🛠️ Stato Carico Operatore")
        mie_assegnate = [p for p in pratiche_data if str(p.get('Email_Operatore', '')).lower() == str(email).lower()]
        notifiche_op = len([p for p in mie_assegnate if str(p.get('Notifica_Nota', '')).strip() == 'Operatore'])
        
        co1, co2 = st.columns(2)
        co1.metric("Pratiche in Carico", len([p for p in mie_assegnate if p.get('Stato_Attuale') not in ['Conclusa', 'Archiviata']]))
        if notifiche_op > 0:
            co2.metric("Note da Richiedenti ✉️", notifiche_op, delta="Urgenti")
        else:
            co2.metric("Note da Richiedenti", 0)
            
        if st.button("🔍 Vai al Pannello Operatore", use_container_width=True):
            st.session_state['current_page'] = "Pannello Operatore"
            st.rerun()
