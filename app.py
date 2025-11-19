import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# --- CONFIGURATION GOOGLE SHEETS ---
# On définit le périmètre (scope) des droits d'accès
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def get_connection():
    # Récupération des secrets depuis Streamlit Cloud
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    client = gspread.authorize(creds)
    # Ouvre le fichier Google Sheet par son nom
    sheet = client.open("Mes Abonnements").sheet1 
    return sheet

# --- FONCTIONS ---
def load_data():
    sheet = get_connection()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["Nom", "Prix", "Périodicité", "Prochaine échéance"])
    return pd.DataFrame(data)

def add_subscription(nom, prix, periodicite, date):
    sheet = get_connection()
    # Ajout d'une ligne dans le Google Sheet
    sheet.append_row([nom, prix, periodicite, str(date)])

def delete_subscription(index_to_delete):
    sheet = get_connection()
    # +2 car Google Sheet commence à 1 et la ligne 1 est le titre
    sheet.delete_rows(index_to_delete + 2) 

# --- INTERFACE ---
st.set_page_config(page_title="Mes Abonnements", page_icon="💳")
st.title("💳 Suivi de mes Abonnements (Cloud)")

# Chargement (peut prendre 1 ou 2 secondes car c'est en ligne)
try:
    df = load_data()
except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.stop()

# --- SIDEBAR : AJOUT ---
with st.sidebar:
    st.header("➕ Ajouter")
    name = st.text_input("Nom du service")
    price = st.number_input("Prix (€)", min_value=0.0, step=0.1, format="%.2f")
    periodicity = st.selectbox("Périodicité", ["Mensuel", "Annuel"])
    date = st.date_input("Prochaine date")
    
    if st.button("Sauvegarder dans le Cloud"):
        add_subscription(name, price, periodicity, date)
        st.success("Enregistré sur Google Drive !")
        st.rerun()

# --- TABLEAU DE BORD ---
if not df.empty:
    # Nettoyage des formats
    df["Prix"] = pd.to_numeric(df["Prix"])
    df["Prochaine échéance"] = pd.to_datetime(df["Prochaine échéance"]).dt.date
    today = datetime.now().date()

    # Calculs
    total_mensuel = 0
    for _, row in df.iterrows():
        if row["Périodicité"] == "Mensuel":
            total_mensuel += row["Prix"]
        else:
            total_mensuel += row["Prix"] / 12
            
    col1, col2 = st.columns(2)
    col1.metric("Abonnements", len(df))
    col2.metric("Coût Mensuel", f"{total_mensuel:.2f} €")
    
    st.markdown("---")

    # Alertes (7 jours)
    st.subheader("⚠️ À venir (7 jours)")
    upcoming = df[(df["Prochaine échéance"] >= today) & 
                  (df["Prochaine échéance"] <= today + timedelta(days=7))]
    
    if not upcoming.empty:
        for _, row in upcoming.iterrows():
            st.warning(f"**{row['Nom']}** : {row['Prix']}€ le {row['Prochaine échéance']}")
    else:
        st.info("Rien à signaler cette semaine.")

    st.markdown("---")
    st.subheader("📋 Liste complète")
    st.dataframe(df)
    
    # Suppression simple
    st.write("---")
    with st.expander("Supprimer un abonnement"):
        options = df["Nom"].tolist()
        to_delete = st.selectbox("Choisir l'abonnement à supprimer", options)
        if st.button("Supprimer définitivement"):
            idx = df[df["Nom"] == to_delete].index[0]
            delete_subscription(idx)
            st.success("Supprimé !")
            st.rerun()

else:
    st.info("Aucun abonnement trouvé sur le Drive. Ajoutes-en un !")