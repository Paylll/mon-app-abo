import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- CONFIGURATION GOOGLE SHEETS (NOUVELLE MÉTHODE) ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_connection():
    # Récupération des secrets
    if "gcp_service_account" not in st.secrets:
        st.error("Les secrets ne sont pas configurés correctement.")
        st.stop()
        
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # Connexion moderne avec google-auth
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    
    # Ouverture du fichier
    # Assure-toi que ton Google Sheet s'appelle bien "Mes Abonnements"
    try:
        sheet = client.open("Mes Abonnements").sheet1
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Impossible de trouver le fichier 'Mes Abonnements'. Vérifie le nom exact sur Google Drive.")
        st.stop()

# --- FONCTIONS ---
def load_data():
    sheet = get_connection()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["Nom", "Prix", "Périodicité", "Prochaine échéance"])
    return pd.DataFrame(data)

def add_subscription(nom, prix, periodicite, date):
    sheet = get_connection()
    sheet.append_row([nom, prix, periodicite, str(date)])

def delete_subscription(nom_to_delete):
    sheet = get_connection()
    # On cherche la cellule qui contient le nom
    cell = sheet.find(nom_to_delete)
    sheet.delete_rows(cell.row)

# --- INTERFACE ---
st.set_page_config(page_title="Mes Abonnements", page_icon="💳")
st.title("💳 Suivi de mes Abonnements (Cloud)")

# Chargement des données
try:
    df = load_data()
except Exception as e:
    st.error(f"Une erreur technique est survenue : {e}")
    st.stop()

# --- SIDEBAR : AJOUT ---
with st.sidebar:
    st.header("➕ Ajouter")
    name = st.text_input("Nom du service")
    price = st.number_input("Prix (€)", min_value=0.0, step=0.1, format="%.2f")
    periodicity = st.selectbox("Périodicité", ["Mensuel", "Annuel"])
    date = st.date_input("Prochaine date")
    
    if st.button("Sauvegarder dans le Cloud"):
        if name:
            add_subscription(name, price, periodicity, date)
            st.success("Enregistré sur Google Drive !")
            st.rerun()
        else:
            st.warning("Le nom est obligatoire.")

# --- TABLEAU DE BORD ---
if not df.empty:
    # Nettoyage et conversion
    # Si le fichier est vide ou mal formaté, on gère l'erreur
    if "Prix" in df.columns and "Prochaine échéance" in df.columns:
        try:
            df["Prix"] = pd.to_numeric(df["Prix"], errors='coerce').fillna(0)
            df["Prochaine échéance"] = pd.to_datetime(df["Prochaine échéance"]).dt.date
        except:
            st.warning("Attention, certaines dates ou prix dans le fichier Excel sont mal écrits.")

        today = datetime.now().date()

        # Calculs
        total_mensuel = 0
        for _, row in df.iterrows():
            p = row["Prix"]
            if row["Périodicité"] == "Mensuel":
                total_mensuel += p
            else:
                total_mensuel += p / 12
                
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
        
        # Suppression
        st.write("---")
        with st.expander("Supprimer un abonnement"):
            options = df["Nom"].tolist()
            if options:
                to_delete = st.selectbox("Choisir l'abonnement à supprimer", options)
                if st.button("Supprimer définitivement"):
                    delete_subscription(to_delete)
                    st.success("Supprimé !")
                    st.rerun()
    else:
        st.error("Les colonnes du fichier Google Sheet ne correspondent pas (Attendu : Nom, Prix, Périodicité, Prochaine échéance)")

else:
    st.info("Aucun abonnement trouvé sur le Drive. Ajoutes-en un !")