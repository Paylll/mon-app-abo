import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# --- CONFIGURATION ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_connection():
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets non configurés.")
        st.stop()
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
    client = gspread.authorize(creds)
    try:
        # --- COLLE TON ID CI-DESSOUS ---
        sheet = client.open_by_key("1LQrmrzx61KSOO1WnoArEXAXQ_idhF1RO__bFJH2LkcU").sheet1
        return sheet
    except Exception as e:
        st.error(f"Erreur ID Google Sheet : {e}")
        st.stop()

# --- FONCTION DE NETTOYAGE (La nouveauté) ---
def nettoyer_prix(valeur):
    """Transforme n'importe quoi (2,99 ou $2.99) en un vrai nombre (2.99)"""
    valeur_str = str(valeur)
    # On enlève les symboles qui gênent ($ et € et espaces)
    valeur_str = valeur_str.replace('€', '').replace('$', '').replace(' ', '')
    # On remplace la virgule par un point
    valeur_str = valeur_str.replace(',', '.')
    try:
        return float(valeur_str)
    except:
        return 0.0

# --- FONCTIONS ---
def load_data():
    sheet = get_connection()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["Nom", "Prix", "Périodicité", "Prochaine échéance"])
    return pd.DataFrame(data)

def add_subscription(nom, prix, periodicite, date):
    sheet = get_connection()
    # On envoie le chiffre brut
    sheet.append_row([nom, float(prix), periodicite, str(date)])

def delete_subscription(nom_to_delete):
    sheet = get_connection()
    try:
        cell = sheet.find(nom_to_delete)
        sheet.delete_rows(cell.row)
    except:
        st.warning("Introuvable.")

# --- INTERFACE ---
st.set_page_config(page_title="Mes Abonnements", page_icon="💳")
st.title("💳 Suivi de mes Abonnements")

try:
    df = load_data()
except:
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("➕ Ajouter")
    name = st.text_input("Nom")
    price = st.number_input("Prix (€)", min_value=0.0, step=0.01, format="%.2f")
    periodicity = st.selectbox("Périodicité", ["Mensuel", "Annuel"])
    date = st.date_input("Prochaine date")
    
    if st.button("Sauvegarder"):
        if name:
            add_subscription(name, price, periodicity, date)
            st.success("Sauvegardé !")
            st.rerun()

# --- TABLEAU DE BORD ---
if not df.empty:
    # --- APPLICATION DU NETTOYAGE ---
    # On applique la fonction nettoyer_prix sur toute la colonne Prix
    df["Prix"] = df["Prix"].apply(nettoyer_prix)
    
    df["Prochaine échéance"] = pd.to_datetime(df["Prochaine échéance"]).dt.date
    today = datetime.now().date()

    # Calculs
    total = 0
    for _, row in df.iterrows():
        if row["Périodicité"] == "Mensuel":
            total += row["Prix"]
        else:
            total += row["Prix"] / 12
            
    col1, col2 = st.columns(2)
    col1.metric("Nombre", len(df))
    col2.metric("Mensuel", f"{total:.2f} €")
    
    st.markdown("---")
    st.subheader("⚠️ Prochains 7 jours")
    upcoming = df[(df["Prochaine échéance"] >= today) & (df["Prochaine échéance"] <= today + timedelta(days=7))]
    
    if not upcoming.empty:
        for _, row in upcoming.iterrows():
            st.warning(f"**{row['Nom']}** : {row['Prix']:.2f} € le {row['Prochaine échéance']}")
    else:
        st.info("Rien à signaler.")

    st.markdown("---")
    st.dataframe(df)
    
    with st.expander("Supprimer"):
        to_del = st.selectbox("Quel abonnement ?", df["Nom"].unique())
        if st.button("Confirmer la suppression"):
            delete_subscription(to_del)
            st.success("Fait !")
            st.rerun()