# Specifiche di Progetto: Sistema di Ticketing Amministrativo Universitario (Streamlit + Google Workspace)

## 1. Panoramica del Progetto
Sviluppo di una Web App serverless per la gestione di procedure amministrative universitarie. L'applicazione (in lingua italiana) funge da sistema di ticketing basato su stati (fasi) con gestione documentale, tracciamento SLA, ruoli gerarchici, anagrafica utenti e generazione dinamica di PDF con carta intestata.

## 2. Stack Tecnologico
* **Frontend & Backend:** Python con framework `Streamlit`.
* **Architettura Codice:** Struttura modulare (es. cartella `/forms`) per definire dinamicamente le interfacce delle singole pratiche in file separati.
* **Database:** Google Sheets (tramite libreria `gspread`).
* **Storage Documentale:** Google Drive (tramite Google Drive API).
* **Autenticazione:** Google OAuth 2.0 (Login con account istituzionale).
* **Generazione PDF:** Libreria Python (es. `ReportLab` o `WeasyPrint`) con supporto per l'inclusione di file SVG (Header e Footer).
* **Invio Email:** SMTP istituzionale o Google Gmail API.

## 3. Ruoli e Permessi (RBAC)
1.  **Responsabile di Piattaforma (Admin):** Gestione utenti, configurazione SLA, upload dei file SVG per la carta intestata dei PDF generati, e definizione dei Modelli/Template di allegati richiesti.
2.  **Responsabile PTA (Dispatcher):** Visualizza le pratiche in ingresso e le assegna agli Operatori PTA (o a sé stesso).
3.  **Operatore PTA (Worker):** Gestisce le pratiche assegnate, cambia le fasi, richiede integrazioni documentali scegliendo da template predefiniti, edita le note condivise.
4.  **Richiedente (Docente/PTA area):** Inserisce nuove pratiche, gestisce il proprio "Profilo Utente", carica documenti se richiesti e monitora l'avanzamento.

## 4. Gestione Profilo Utente (Richiedente)
Ogni Richiedente ha a disposizione una pagina "Profilo" in cui gestire i propri dati, che verranno usati per pre-compilare le richieste:
* **Dati Anagrafici:** Nome, Cognome, Data e Luogo di nascita, Ruolo Accademico.
* **Elenco Progetti di Ricerca (CRUD):** L'utente può aggiungere, rimuovere o modificare i propri progetti. [cite_start]Per ogni progetto definisce: `Nome Progetto`, `Acronimo`, e `Codice CUP`[cite: 8].

## 5. Tipologie di Pratiche e Maschere di Inserimento (Modulari)
Le logiche e i form delle pratiche devono risiedere in file Python separati (es. `forms/acquisti.py`, `forms/contratti.py`) per permettere una facile manutenzione e la futura aggiunta di nuove tipologie.

### 5.1 Pratica "Acquisto"
[cite_start]Ispirata al modello standard di richiesta acquisto bene/servizio[cite: 4]. Il form deve includere:
* [cite_start]**Progetto:** Menu a tendina popolato automaticamente dall'elenco progetti del Profilo Utente (che recupera in automatico Titolare e CUP)[cite: 6, 8].
* [cite_start]**Oggetto dell'Acquisto:** Descrizione dettagliata dei beni e/o servizi necessari e coerenti con le finalità del Progetto[cite: 10].
* [cite_start]**Codice CPV:** Campo testuale[cite: 11].
* [cite_start]**Motivazioni:** Area di testo[cite: 12].
* [cite_start]**Importo:** Spesa presunta in € + IVA[cite: 14, 15].
* **Gestione Inventario (Logica Condizionale):**
    * Checkbox/Radio: Il bene è inventariabile? (Sì / No) [cite_start][cite: 17, 19].
    * *Se Sì:*
        * [cite_start]Ubicazione: Stanza n., Cubo n., Piano[cite: 17, 20].
        * [cite_start]Responsabilità: Radio button (Sotto la responsabilità del sottoscritto / Assegnato a: [Campo di testo])[cite: 21, 23].
        * [cite_start]Dichiarazione ammortamento: Checkbox (Ammortizzato in 36 mesi - 33,33%)[cite: 26].

### 5.2 Pratica "Contratti"
Form definito nel modulo `forms/contratti.py` (Campi da definire: Contraente, Oggetto, Importo, Durata, ecc.).

## 6. Logica di Business e Workflow

### 6.1 Fasi, Timestamping e SLA
* Ogni cambio di fase registra Data/Ora Inizio e Data/Ora Fine.
* Il sistema calcola gli SLA. Colori cruscotto Operatore:
    * **Rosso:** Pratica scaduta.
    * **Arancione:** Pratica in scadenza (tempo rimanente <= 20% del totale).

### 6.2 Campo "Note Condivise"
All'interno di ogni singola pratica è presente un'area di testo ("Note di Pratica") editabile in qualsiasi momento sia dall'Operatore che dal Richiedente, per comunicazioni rapide o appunti non strutturati.

### 6.3 Stato Sospeso: "In attesa di riscontro" e Template Documenti
* L'Operatore può mettere la pratica "In attesa di riscontro".
* Durante questa operazione, l'Operatore deve poter selezionare (da un menu a tendina) il **Format dell'Allegato** richiesto. Questa lista è predefinita nel sistema (es. "Modulo Tracciabilità Flussi", "Dichiarazione di Unicità") e include il Titolo e il Link per scaricare il template vuoto.
* Il Richiedente viene notificato, scarica il format, lo compila e lo ricarica sulla piattaforma tramite apposito `st.file_uploader`.
* **Blocco SLA:** I giorni trascorsi in questo stato non vengono conteggiati nel calcolo globale degli SLA.

### 6.4 Generazione PDF e Chiusura
1.  **Avvio Pratica:** Al submit di una richiesta, il sistema genera un PDF riepilogativo. Il PDF deve includere come Header e Footer i file SVG (Carta Intestata) caricati dall'Admin. Il file viene inviato via email al Richiedente.
2.  **Chiusura Pratica:** Quando la pratica passa a "Conclusa", viene generato un PDF di "Sommario Finale" (con cronologia). Questo PDF e tutti gli allegati scambiati vengono inseriti in un archivio `.zip`, salvato su Google Drive, e la pratica viene archiviata.

## 7. Struttura del Database (Google Sheets)
* `Utenti`: ID, Email, Nome, Cognome, Data_Nascita, Luogo_Nascita, Ruolo_Accademico, Ruolo_Sistema.
* `Progetti_Utenti`: ID_Record, Email_Utente, Nome_Progetto, Acronimo, CUP.
* `Impostazioni_Sistema`: Chiave, Valore (es. Link al file SVG Header, Link al file SVG Footer).
* `Template_Documenti`: ID, Tipo_Pratica, Titolo_Documento, Link_URL.
* `Configurazione_Pratiche`: Tipo_Pratica, Giorni_SLA_Totali.
* `Pratiche`: ID_Pratica, Email_Richiedente, Email_Operatore, Tipo, Stato_Attuale, Dati_JSON (per salvare dinamicamente i campi dei form modulari), Note_Condivise, Data_Creazione, Link_Zip.
* `Storico_Fasi`: ID_Record, ID_Pratica, Nome_Fase, Data_Inizio, Data_Fine, Sospensione_SLA (Booleano).
* `Allegati`: ID_File, ID_Pratica, Nome_File, URL_Drive, Caricato_da.