import os
import json
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo # Standard en Python 3.9+

def update_live_json():
    # 1. Heure locale française (Paris, avec la prise en compte de l'heure d'été UTC+2)
    now_local = datetime.now(ZoneInfo("Europe/Paris"))
    
    # 2. Décalage de 3 ans basé sur l'heure locale (ex: 11h59 en 2026 -> 11h59 en 2023)
    target_date = now_local.replace(year=now_local.year - 3).replace(tzinfo=None)
    
    csv_path = 'data_2023.csv'
    
    if not os.path.exists(csv_path):
        print(f"Erreur : Le fichier {csv_path} est introuvable.")
        return

    df = pd.read_csv(csv_path)
    df['TIMESTAMP_UTC'] = pd.to_datetime(df['TIMESTAMP_UTC'])
    
    # 3. Recherche de la ligne la plus proche de l'heure locale
    df['diff'] = (df['TIMESTAMP_UTC'] - target_date).abs()
    closest = df.sort_values('diff').iloc[0]
    
    def clean_val(val):
        if pd.isna(val) or str(val).strip().upper() in ['NAN', 'NONE', '']:
            return None
        try:
            return round(float(val), 4)
        except:
            return str(val)

    # 4. Construction du payload avec les variables spécifiques à l'arbre 09
    payload = {
        "timestamp_local_2026": now_local.strftime('%Y-%m-%d %H:%M:%S'),
        "replay_timestamp_2023": closest['TIMESTAMP_UTC'].strftime('%Y-%m-%d %H:%M:%S'),
        "Rain_mm": clean_val(closest.get('Rain_mm')),
        "SlrFD_avg": clean_val(closest.get('SlrFD_avg')),
        "AirTC_1_avg": clean_val(closest.get('AirTC_1_avg')),
        "Tair_avg": clean_val(closest.get('Tair_avg')),
        "VWC_50cm": clean_val(closest.get('VWC_50cm')),
        "SF_diff_arbre09": clean_val(closest.get('SF_diff')), 
        "LVDT_diff_arbre09": clean_val(closest.get('LVDT_diff')),
        "year": clean_val(closest.get('year')),
        "cumulative_rai": clean_val(closest.get('cumulative_rai'))
    }

    os.makedirs('data', exist_ok=True)
    with open('data/live.json', 'w') as f:
        json.dump(payload, f, indent=2)

    print(" data/live.json mis à jour (Heure Locale Paris) :")
    print(json.dumps(payload, indent=2))

if __name__ == '__main__':
    update_live_json()
