import streamlit as st
import datetime
from dotenv import load_dotenv

# Carica esplicitamente il .env per testing locale
load_dotenv()

# Configure main page BEFORE any other Streamlit calls
st.set_page_config(
    page_title="HipA - Piattaforma Ticketing", 
    page_icon="🎓", 
    layout="wide"
)

# Custom CSS for blinking notification
st.markdown("""
    <style>
    @keyframes blink {
        0% { opacity: 1; }
        50% { opacity: 0.2; }
        100% { opacity: 1; }
    }
    .blink-icon {
        animation: blink 1.2s infinite;
        font-size: 1.3rem;
        vertical-align: middle;
    }
    </style>
""", unsafe_allow_html=True)

# Import internal modules
from core.auth import check_login, logout
from core.google_api import g_api
from forms.dashboard import show_dashboard
from forms.profilo import show_profilo
from forms.acquisti import show_acquisti_form
from forms.contratti import show_contratti_form
from forms.dettaglio import show_dettaglio_pratica

def init_session_state():
    """Inizializza tutte le chiavi necessarie nello stato della sessione per evitare KeyError"""
    keys_default = {
        'logged_in': False,
        'user_email': None,
        'user_given_name': None,
        'user_family_name': None,
        'user_role': None,         # Verrà recuperato dal DB
        'first_login': False,      # Se vero, mostra form anagrafica
        'current_page': 'Dashboard',
        'waiting_approval': False
    }
    for k, v in keys_default.items():
        if k not in st.session_state:
            st.session_state[k] = v

def verify_user_in_db():
    """Controlla se l'utente esiste in Utenti. Se no, attiva first_login."""
    email = st.session_state['user_email']
    # Recupera i dati del DB
    users_data = g_api.get_sheet_data('Utenti')
    
    user_record = next((u for u in users_data if str(u.get('Email', '')).lower() == str(email).lower()), None)
    
    if not user_record:
        st.session_state['first_login'] = True
        st.session_state['user_role'] = 'Richiedente'
    else:
        st.session_state['first_login'] = False
        stato = user_record.get('Stato', 'Attivo') # Fallback per sicurezza
        if stato == 'In Attesa':
            st.session_state['waiting_approval'] = True
        else:
            st.session_state['waiting_approval'] = False
            st.session_state['user_role'] = user_record.get('Ruolo_Sistema', 'Richiedente')

def show_first_login_form():
    """Mostra un form per far inserire i dati anagrafici al primo accesso."""
    st.subheader("🎉 Benvenuto in HipA!")
    st.write("Sembra che sia il tuo primo accesso. Completa il tuo profilo per continuare.")
    
    with st.form("first_login_form"):
        col1, col2 = st.columns(2)
        with col1:
             nome = st.text_input("Nome", value=st.session_state.get('user_given_name', ''))
             luogo_nascita = st.text_input("Luogo di Nascita")
        with col2:
             cognome = st.text_input("Cognome", value=st.session_state.get('user_family_name', ''))
             data_nascita = st.date_input("Data di Nascita", min_value=datetime.date(1930, 1, 1), max_value=datetime.date.today())
        
        ruoli_accademici = ["Docente", "Ricercatore", "Assegnista", "Dottorando", "PTA", "Altro"]
        ruolo_accademico = st.selectbox("Ruolo Accademico", ruoli_accademici)
        
        submitted = st.form_submit_button("Salva e Continua", type="primary")
        
        if submitted:
            if not nome or not cognome or not luogo_nascita:
                st.error("Per favore, compila tutti i campi.")
            else:
                 # Salva su Google Sheets nel foglio 'Utenti'
                 # Colonne attese: ID, Email, Nome, Cognome, Data_Nascita, Luogo_Nascita, Ruolo_Accademico, Ruolo_Sistema
                 users_data = g_api.get_sheet_data('Utenti')
                 
                 # Double check per evitare duplicati se l'utente clicca più volte o ricarica
                 exists = any(str(u.get('Email', '')).lower() == st.session_state['user_email'].lower() for u in users_data)
                 
                 if not exists:
                     new_id = len(users_data) + 1 # Generazione ID molto basic
                     
                     new_row = [
                         new_id, 
                         st.session_state['user_email'],
                         nome,
                         cognome,
                         str(data_nascita),
                         luogo_nascita,
                         ruolo_accademico,
                         "Richiedente", # Ruolo_Sistema base assegnato
                         "In Attesa"    # Stato: richiede approvazione
                     ]
                     
                     success = g_api.append_row('Utenti', new_row)
                 else:
                     success = True # Consideriamolo un successo se esiste già
                 if success:
                                   st.session_state['first_login'] = False
                                   st.session_state['waiting_approval'] = True
                                   st.session_state['user_given_name'] = nome
                                   st.session_state['user_family_name'] = cognome
                                   st.success("Richiesta inviata con successo! Sarai abilitato al termine delle verifiche amministrative.")
                                   st.rerun()

def main():
    init_session_state()

    # Se non siamo loggati, mostra pagina esterna e ferma l'esecuzione qui
    is_authenticated = check_login()
    if not is_authenticated:
        return

    # Se l'utente è loggato in OAuth, ma non abbiamo ancora controllato il DB
    if st.session_state['user_role'] is None and not st.session_state['first_login']:
         with st.spinner("Controllo credenziali in corso..."):
              verify_user_in_db()

    # Router interno
    if st.session_state.get('first_login'):
         show_first_login_form()
    elif st.session_state.get('waiting_approval'):
         st.warning("⏳ Accesso in attesa di approvazione")
         st.write(f"Gentile {st.session_state.get('user_given_name')}, la tua richiesta di accesso al sistema HipA è stata registrata.")
         st.write("Un amministratore deve verificare e approvare il tuo account prima che tu possa accedere alle funzionalità del portale.")
         st.info("Riceverai una notifica o potrai riprovare l'accesso più tardi.")
         if st.button("Logout"):
              logout()
    else:
         # Costruzione della Sidebar per la navigazione
         with st.sidebar:
              st.markdown(f"**Utente:** {st.session_state.get('user_given_name')} {st.session_state.get('user_family_name')}")
              st.markdown(f"**Ruolo:** {st.session_state.get('user_role')}")
              st.markdown("---")
              
              pages = ["Dashboard", "Pannello Richiedente", "Il mio Profilo", "Nuova Pratica"]
              
              # Pannello Operatore per lavoratori (Worker/Dispatcher) e Admin (per test)
              if st.session_state['user_role'] in ['Worker', 'Dispatcher', 'Admin']:
                  pages.append("Pannello Operatore")
              
              # Pannello Admin solo per Admin
              if st.session_state['user_role'] == 'Admin':
                  pages.append("Pannello Admin")
                  
              st.markdown("**Navigazione**")
              current = st.session_state.get('current_page', 'Dashboard')
              for p in pages:
                  if st.button(p, key=f"nav_{p}", use_container_width=True, type="primary" if current == p else "secondary"):
                      st.session_state['current_page'] = p
                      st.rerun()
              
              st.markdown("---")
              if st.button("Logout"):
                  logout()

         # Content Switcher
         page = st.session_state.get('current_page', 'Dashboard')
         
         if page == "Dashboard":
              from forms.dashboard import show_home_dashboard
              show_home_dashboard()
              
         elif page == "Pannello Richiedente":
              from forms.dashboard import show_richiedente_dashboard
              show_richiedente_dashboard(st.session_state['user_email'])
         
         # Pannello operatore esplicito (per lavorare le proprie pratiche)
         elif page == "Pannello Operatore":
              from forms.dashboard import show_worker_dashboard
              show_worker_dashboard(st.session_state['user_email'])
              
         # Pannello admin esplicito (supervisione)
         elif page == "Pannello Admin":
              from forms.dashboard import show_admin_dashboard
              show_admin_dashboard()

         elif page == "Dettaglio Pratica":
              show_dettaglio_pratica()

         elif page == "Il mio Profilo":
              show_profilo()
         elif page == "Nuova Pratica":
              st.title("Nuova Pratica")
              tipo_pratica = st.selectbox("Seleziona la tipologia di pratica", 
                                          ["-- Seleziona --", "Acquisto Beni/Servizi", "Contratti"])
              
              if tipo_pratica == "Acquisto Beni/Servizi":
                  # Carichiamo i progetti dell'utente
                  email = st.session_state.get('user_email')
                  progetti_data = g_api.get_sheet_data('Progetti_Utenti')
                  miei_progetti = [p for p in progetti_data if str(p.get('Email_Utente', '')).lower() == str(email).lower()]
                  
                  if miei_progetti:
                       show_acquisti_form(miei_progetti)
                  else:
                       st.warning("Devi prima registrare almeno un 'Progetto di Ricerca' dal tuo Profilo per poter avviare questa pratica.")
                       
              elif tipo_pratica == "Contratti":
                  # Carichiamo i progetti dell'utente
                  email = st.session_state.get('user_email')
                  progetti_data = g_api.get_sheet_data('Progetti_Utenti')
                  miei_progetti = [p for p in progetti_data if str(p.get('Email_Utente', '')).lower() == str(email).lower()]
                  
                  if miei_progetti:
                       show_contratti_form(miei_progetti)
                  else:
                       st.warning("Devi prima registrare almeno un 'Progetto di Ricerca' dal tuo Profilo per poter avviare questa pratica.")

if __name__ == "__main__":
    main()
