import datetime
import pandas as pd
import numpy as np

def _get_business_days(start_date, end_date):
    """Calcola i giorni lavorativi (lunedì-venerdì) tra due date lavorando con pandas."""
    # freq='B' means business days
    try:
        days = pd.bdate_range(start=start_date, end=end_date)
        return len(days)
    except Exception:
         return 0

def calculate_sla_status(data_creazione_str: str, giorni_totali: int, periodi_sospensione: list) -> dict:
    """
    Calcola lo stato attuale dell'SLA.
    :param data_creazione_str: Data creazione pratica (formato stringa ISO)
    :param giorni_totali: Quanti giorni lavorativi di SLA massimi
    :param periodi_sospensione: una lista di dict del tipo [{'inizio': '2026-...', 'fine': '2026-... o None'}]
    :return: dict con 'status' ('Verde', 'Arancione', 'Rosso'), 'giorni_trascorsi', 'giorni_rimanenti'
    """
    try:
         data_creazione = pd.to_datetime(data_creazione_str).tz_localize(None)
    except:
         data_creazione = datetime.datetime.now()

    oggi = datetime.datetime.now()
    
    # 1. Calcolo giorni lavorativi totali trascorsi dalla creazione
    giorni_lavorativi_assoluti = _get_business_days(data_creazione.date(), oggi.date())
    
    # 2. Sottrazione giorni di sospensione
    giorni_sospesi = 0
    for ps in periodi_sospensione:
         inz = pd.to_datetime(ps['inizio']).tz_localize(None).date()
         fin = pd.to_datetime(ps['fine']).tz_localize(None).date() if ps.get('fine') else oggi.date()
         
         if inz <= oggi.date():
              # Calcola i giorni business di sospensione e li sottrae dal conteggio test
              giorni_sospesi += _get_business_days(inz, min(fin, oggi.date()))
    
    # I giorni effettivamente consumati della pratica
    giorni_effettivi = max(0, giorni_lavorativi_assoluti - giorni_sospesi)
    
    giorni_rimanenti = giorni_totali - giorni_effettivi
    
    status = "Verde"
    if giorni_rimanenti < 0:
         status = "Rosso"
    elif giorni_rimanenti <= (giorni_totali * 0.2): # Meno del 20% del tempo rimanente
         status = "Arancione"
         
    return {
         'status': status,
         'giorni_trascorsi': giorni_effettivi,
         'giorni_rimanenti': giorni_rimanenti
    }
