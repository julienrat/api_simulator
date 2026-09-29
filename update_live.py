import os
import json
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Standard en Python 3.9+

RAW_PATH = 'RAWDATA_Foret expérimentale_Données capteurs_Juillet à Octobre 2023_ReadMe-Original.xlsx'
RAW_SHEET = 'RAWDATA_Foret expérimentale_Don'
QUPU_PATH = 'QUPU009_daily.xlsx'
QUPU_SHEET = 'QUPU009_daily'

# Écart max toléré entre l'heure cible et la ligne RAWDATA la plus proche
# (les données sont toutes les 30 min). Au-delà, on considère qu'il n'y a pas de donnée.
RAW_TOLERANCE = timedelta(minutes=30)

# True  : 12h30 heure de Paris en 2026 -> ligne RAWDATA de 12h30 heure de Paris en 2023
#         (soit 10h30 UTC en été). C'est le "vrai" rejeu à la même heure locale.
# False : 12h30 en 2026 -> ligne RAWDATA étiquetée 12h30 (UTC) en 2023,
#         sans conversion (comportement de la toute première version).
ALIGN_ON_LOCAL_TIME = True

# clé du payload -> (colonne dans RAWDATA, colonne dans QUPU009_daily)
# None = la variable n'existe pas dans cette source
FIELDS = {
    "Rain_mm":           (None,             "Rain_mm"),
    "SlrFD_avg":         (None,             "SlrFD_avg"),
    "AirTC_1_avg":       (None,             "AirTC_1_avg"),
    "Tair_avg":          ("AirTC_Avg",      "Tair_avg"),
    "VWC_50cm":          ("VWC_50cm_Avg",   "VWC_50cm"),
    "SF_diff_arbre09":   ("SF_tree_09_Avg", "SF_diff"),
    "LVDT_diff_arbre09": ("LVDT_tree_09_Avg", "LVDT_diff"),
    "cumulative_rai":    (None,             "cumulative_rain"),
}


def clean_val(val):
    """Renvoie un float arrondi, ou None si la valeur est absente / invalide."""
    if val is None or pd.isna(val) or str(val).strip().upper() in ['NAN', 'NONE', '']:
        return None
    try:
        return round(float(val), 4)
    except (TypeError, ValueError):
        return str(val)


def update_live_json(now_local=None):
    # 1. Heure locale française (Paris, avec prise en compte de l'heure d'été)
    if now_local is None:
        now_local = datetime.now(ZoneInfo("Europe/Paris"))

    # 2. Décalage de 3 ans. La colonne TIMESTAMP_UTC est en UTC : on convertit
    #    donc l'heure locale en UTC avant de reculer l'année.
    if ALIGN_ON_LOCAL_TIME:
        base = now_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    else:
        base = now_local.replace(tzinfo=None)
    try:
        target_date = base.replace(year=base.year - 3)
    except ValueError:  # 29 février -> 28 février
        target_date = base.replace(year=base.year - 3, day=28)

    def to_display(ts):
        """Heure affichée dans le JSON : heure locale de Paris (comme timestamp_local_2026)."""
        if not ALIGN_ON_LOCAL_TIME:
            return ts
        return (ts.replace(tzinfo=ZoneInfo("UTC"))
                  .astimezone(ZoneInfo("Europe/Paris"))
                  .replace(tzinfo=None))

    # 3. Source 1 : RAWDATA haute fréquence (Juillet à Octobre 2023)
    closest = None
    if os.path.exists(RAW_PATH):
        df = pd.read_excel(RAW_PATH, sheet_name=RAW_SHEET)
        df['TIMESTAMP_UTC'] = pd.to_datetime(df['TIMESTAMP_UTC'])
        df = df.dropna(subset=['TIMESTAMP_UTC'])
        df['diff'] = (df['TIMESTAMP_UTC'] - target_date).abs()
        row = df.sort_values('diff').iloc[0]
        if row['diff'] <= RAW_TOLERANCE:
            closest = row
        else:
            print(f"RAWDATA : pas de ligne à moins de {RAW_TOLERANCE} de {target_date} "
                  f"(plage {df['TIMESTAMP_UTC'].min()} -> {df['TIMESTAMP_UTC'].max()}), "
                  f"tout sera lu dans QUPU.")
    else:
        print(f"Attention : {RAW_PATH} introuvable, tout sera lu dans QUPU.")

    # 4. Source 2 : QUPU009_daily (valeurs journalières), chargée seulement si besoin
    qupu_row = None
    qupu_loaded = False

    def get_qupu_row():
        nonlocal qupu_row, qupu_loaded
        if not qupu_loaded:
            qupu_loaded = True
            if not os.path.exists(QUPU_PATH):
                print(f"Attention : {QUPU_PATH} introuvable, pas de repli possible.")
            else:
                q = pd.read_excel(QUPU_PATH, sheet_name=QUPU_SHEET)
                q['date'] = pd.to_datetime(q['date']).dt.normalize()
                match = q[q['date'] == pd.Timestamp(to_display(target_date).date())]
                if match.empty:
                    print(f"QUPU : aucune ligne pour le {to_display(target_date).date()}.")
                else:
                    qupu_row = match.iloc[0]
        return qupu_row

    # 5. Pour chaque variable : RAWDATA d'abord, sinon QUPU
    payload = {
        "timestamp_local_2026": now_local.strftime('%Y-%m-%d %H:%M:%S'),
        "replay_timestamp_2023": to_display(
            target_date if closest is None else closest['TIMESTAMP_UTC'].to_pydatetime()
        ).strftime('%Y-%m-%d %H:%M:%S'),
    }
    sources = {}

    for key, (raw_col, qupu_col) in FIELDS.items():
        value, source = None, None

        if closest is not None and raw_col is not None and raw_col in closest.index:
            value = clean_val(closest[raw_col])
            if value is not None:
                source = 'RAWDATA'

        if value is None:
            row = get_qupu_row()
            if row is not None and qupu_col in row.index:
                value = clean_val(row[qupu_col])
                if value is not None:
                    source = 'QUPU'

        payload[key] = value
        sources[key] = source or 'absent'

    payload["year"] = to_display(target_date).year

    # 6. Écriture du fichier JSON ultra-léger pour l'ESP32
    os.makedirs('data', exist_ok=True)
    with open('data/live.json', 'w') as f:
        json.dump(payload, f, indent=2)

    print(" data/live.json mis à jour avec succès :")
    print(json.dumps(payload, indent=2))
    print("Origine des valeurs :", json.dumps(sources, indent=2))
    return payload


if __name__ == '__main__':
    update_live_json()
