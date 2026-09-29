import os
import json
import pandas as pd
from datetime import datetime, timezone

def update_live_json():
    # 1. Heure actuelle en UTC (Norme Python 3.12+)
    now = datetime.now(timezone.utc)
    
    # 2. Décalage temporel : - 3 ans (2026 -> 2023)
    target_date = now.replace(year=now.year - 3).replace(tzinfo=None)
    
    # 3. Nom exact du fichier
    excel_path = 'RAWDATA_Foret expérimentale_Données capteurs_Juillet à Octobre 2023_ReadMe-Original.xlsx'
    
    if not os.path.exists(excel_path):
        print(f"Erreur : Le fichier {excel_path} est introuvable.")
        return

    print("Chargement du fichier Excel (cela peut prendre environ 15-20 secondes)...")
    
    # 4. Lecture de la bonne feuille
    df = pd.read_excel(excel_path, sheet_name='RAWDATA_Foret expérimentale_Don')
    df['TIMESTAMP_UTC'] = pd.to_datetime(df['TIMESTAMP_UTC'])
    
    # 5. Recherche du relevé le plus proche de la minute actuelle simulée en 2023
    df['diff'] = (df['TIMESTAMP_UTC'] - target_date).abs()
    closest = df.sort_values('diff').iloc[0]
    
    # 6. Fonction de nettoyage pour gérer les NaN (valeurs manquantes) -> null en JSON
    def clean_val(val):
        if pd.isna(val) or str(val).strip().upper() in ['NAN', 'NONE', '']:
            return None
        try:
            return round(float(val), 4) # Arrondi à 4 décimales pour alléger
        except:
            return str(val)

    # 7. Création de la réponse JSON ultra-légère pour l'ESP32
    payload = {
        "timestamp_now_2026": now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "replay_timestamp_2023": closest['TIMESTAMP_UTC'].strftime('%Y-%m-%dT%H:%M:%SZ'),
        "temp_air_deg": clean_val(closest.get('AirTC_Avg')),
        "flux_seve_arbre07": clean_val(closest.get('SF_tree_07_Avg')),
        "dendrometre_arbre07": clean_val(closest.get('LVDT_tree_07_Avg')),
        "humidite_sol_5cm": clean_val(closest.get('VWC_5cm_Avg')),
        "temp_sol_5cm": clean_val(closest.get('T_5cm_Avg'))
    }

    # 8. Sauvegarde dans le dossier data/
    os.makedirs('data', exist_ok=True)
    with open('data/live.json', 'w') as f:
        json.dump(payload, f, indent=2)

    print("Succès ! Voici le contenu généré pour l'ESP32 :")
    print(json.dumps(payload, indent=2))

if __name__ == '__main__':
    update_live_json()
