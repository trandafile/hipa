import sys
import os
# Aggiungi il percorso root al path per poter importare 'core'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.pdf_generator import genera_pdf_pratica

dati_test = {
    "progetto_string": "Ricerca AI Applicata (AI-01) - CUP: 123456789",
    "oggetto": "Acquisto Server GPU per addestramento modelli linguistici",
    "motivazioni": "Il server è fondamentale per ridurre i tempi di inferenza e testare i nuovi modelli open source locally.",
    "importo_netto": 8500.0,
    "iva": "22%",
    "totale": 10370.0,
    "inventariabile": "Sì",
    "ubicazione": "Cubo 41C - Piano 5 - Stanza Server",
    "responsabilita": "Assegnato a terzi",
    "assegnatario": "Mario Rossi",
    "ammortamento": True
}

if __name__ == "__main__":
    print("Test generazione PDF...")
    pdf_bytes = genera_pdf_pratica(
        pratica_id="PR-TEST-0001",
        tipo="Acquisto",
        richiedente="luigi.boccia@unical.it",
        data_creazione="2026-02-27 15:30:00",
        stato_attuale="Conclusa",
        dati_json=dati_test
    )
    
    with open("test_generazione.pdf", "wb") as f:
        f.write(pdf_bytes)
        
    print("File test_generazione.pdf salvato con successo.")
