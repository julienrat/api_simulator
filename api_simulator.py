import pandas as pd
import json

# Charger les données brutes
df = pd.read_excel('RAWDATA_Foret expérimentale_Données capteurs_Juillet à Octobre 2023_ReadMe-Original.xlsx', sheet_name='RAWDATA_Foret expérimentale_Don')

# Filtrer et nettoyer les colonnes principales
df['TIMESTAMP_UTC'] = pd.to_datetime(df['TIMESTAMP_UTC'])
df = df.dropna(subset=['TIMESTAMP_UTC'])

# Exporter au format JSON optimisé par mois
df['month'] = df['TIMESTAMP_UTC'].dt.strftime('%Y-%m')
for month, group in df.groupby('month'):
    group.to_json(f'public/data/{month}.json', orient='records', date_format='iso')
