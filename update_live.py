import os
import json
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo  # Standard en Python 3.9+

def update_live_json():
    # 1. Heure locale française (Paris, avec prise en compte de l'heure d'été UTC+2)
    now_local = datetime.now(ZoneInfo("Europe/Paris"))
    
    # 2. Décalage de 3 ans basé sur l'heure locale (ex: 12h30 en 2026 -> 12h30 en 2023)
    target_date = now_local.replace(year=now_local.year - 3).replace(tzinfo=None)
    
    # Fichier source haute fréquence (Juillet à Octobre 2023)
    excel_path = 'RAWDATA_Foret expérimentale_Données capteurs_Juillet à Octobre 2023_ReadMe-Original.xlsx'
    
    if not os.path.exists(excel_path):
        print(f"Erreur : Le fichier {excel_path} est introuvable.")
        return

    # 3. Lecture du fichier Excel (feuille des données brutes)
    df = pd.read_excel(excel_path, sheet_name='RAWDATA_Foret expérimentale_Don')
    df['TIMESTAMP_UTC'] = pd.to_datetime(df['TIMESTAMP_UTC'])
    
    # 4. Recherche de la ligne la plus proche de l'heure cible (intervalle de 30 min)
    df['diff'] = (df['TIMESTAMP_UTC'] - target_date).abs()
    closest = df.sort_values('diff').iloc[0]
    
    # Fonction de nettoyage des valeurs (gestion des NaN / Null)
    def clean_val(val):
        if pd.isna(val) or str(val).strip().upper() in ['NAN', 'NONE', '']:
            return None
        try:
            return round(float(val), 4)
        except:
            return str(val)

    # 5. Payload demandé avec les variables de l'arbre 09 et du contexte
    payload = {
        "timestamp_local_2026": now_local.strftime('%Y-%m-%d %H:%M:%S'),
        "replay_timestamp_2023": closest['TIMESTAMP_UTC'].strftime('%Y-%m-%d %H:%M:%S'),
        "Rain_mm": clean_val(closest.get('Rain_mm')),
        "SlrFD_avg": clean_val(closest.get('SlrFD_avg')),
        "AirTC_1_avg": clean_val(closest.get('AirTC_1_avg')),
        "Tair_avg": clean_val(closest.get('AirTC_Avg')),
        "VWC_50cm": clean_val(closest.get('VWC_50cm_Avg')),
        "SF_diff_arbre09": clean_val(closest.get('SF_tree_09_Avg')),
        "LVDT_diff_arbre09": clean_val(closest.get('LVDT_tree_09_Avg')),
        "year": clean_val(target_date.year),
        "cumulative_rai": clean_val(closest.get('cumulative_rai'))
    }

    # 6. Écriture du fichier JSON ultra-léger pour l'ESP32
    os.makedirs('data', exist_ok=True)
    with open('data/live.json', 'w') as f:
        json.dump(payload, f, indent=2)

    print(" data/live.json mis à jour avec succès :")
    print(json.dumps(payload, indent=2))

if __name__ == '__main__':
    update_live_json()
