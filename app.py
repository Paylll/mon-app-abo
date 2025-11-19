import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- CONFIGURATION GOOGLE SHEETS ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("Les secrets ne sont pas configurés.")
        st.stop()
        
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    
    try:
        # -------------------------------------------------------
        # COLLE TON ID CI-DESSOUS À LA PLACE DE "METS_TON_ID_ICI"
        # -------------------------------------------------------
        sheet = client.open_by_key("1LQrmrzx61KSOO1WnoArEXAXQ_idhF1RO__bFJH2LkcU").sheet1
        return sheet
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        st.stop()

# --- FONCTIONS ---
def load_data():
    sheet = get_connection()
    data = sheet.get_all_records()
    # Si vide, on renvoie un tableau vide avec les bonnes colonnes
    if not data:
        return pd.DataFrame(columns=["Nom", "Prix", "Périodicité", "Prochaine échéance"])
    return pd.DataFrame(data)

def add_subscription(nom, prix, periodicite, date):
    sheet = get_connection()
    # CORRECTION ICI : On transforme le prix 2.99 en "2,99" pour Google Sheet France
    prix_fr = str(prix).replace('.', ',')
    sheet.append_row([nom, prix_fr, periodicite, str(date)])

def delete_subscription(nom_to_delete):
    sheet = get_connection()
    try:
        cell = sheet.find(nom_to_delete)
        sheet.delete_rows(cell.row)
    except:
        st.warning("Impossible de supprimer, ligne introuvable.")

# --- INTERFACE ---
st.set_page_config(page_title="Mes Abonnements", page_icon="💳")
st.title("💳 Suivi de mes Abonnements (Cloud)")

# Chargement des données
try:
    df = load_data()
except Exception as e:
    st.error(f"Erreur de chargement : {e}")
    st.stop()

# --- SIDEBAR : AJOUT ---
with st.sidebar:
    st.header("➕ Ajouter")
    name = st.text_input("Nom du service")
    # format="%.2f" permet de saisir des décimales
    price = st.number_input("Prix (€)", min_value=0.0, step=0.01, format="%.2f")
    periodicity = st.selectbox("Périodicité", ["Mensuel", "Annuel"])
    date = st.date_input("Prochaine date")
    
    if st.button("Sauvegarder dans le Cloud"):
        if name:
            add_subscription(name, price, periodicity, date)
            st.success("Enregistré (avec virgule) !")
            st.rerun()
        else:
            st.warning("Le nom est obligatoire.")

# --- TABLEAU DE BORD ---
if not df.empty:
    if "Prix" in df.columns and "Prochaine échéance" in df.columns:
        
        # --- NETTOYAGE DES DONNÉES (Lecture) ---
        # 1. On remplace les virgules par des points pour que Python puisse calculer
        df["Prix"] = df["Prix"].astype(str).str.replace(',', '.')
        # 2. On convertit en nombre
        df["Prix"] = pd.to_numeric(df["Prix"], errors='coerce').fillna(0)
        
        # 3. Gestion des dates
        df["Prochaine échéance"] = pd.to_datetime(df["Prochaine échéance"]).dt.date

        today = datetime.now().date()

        # Calculs financiers
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
        st.error("Colonnes incorrectes dans Google Sheet.")

else:
    st.info("Aucun abonnement trouvé. Ajoutes-en un !")