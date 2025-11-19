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

# --- FONCTIONS ---
def load_data():
    sheet = get_connection()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["Nom", "Prix", "Périodicité", "Prochaine échéance"])
    return pd.DataFrame(data)

def add_subscription(nom, prix, periodicite, date):
    sheet = get_connection()
    
    # --- LA CORRECTION EST ICI ---
    # 1. On prend le prix (ex: 2.99)
    # 2. On le formate avec 2 décimales et on remplace le POINT par une VIRGULE
    prix_fr = f"{prix:.2f}".replace('.', ',') # Devient "2,99" (Texte)
    
    # 3. On envoie avec l'option 'USER_ENTERED' pour que Google Sheet comprenne la virgule
    sheet.append_row([nom, prix_fr, periodicite, str(date)], value_input_option='USER_ENTERED')

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
            st.success("Sauvegardé avec virgule !")
            st.rerun()

# --- TABLEAU DE BORD ---
if not df.empty:
    # Nettoyage lecture
    df["Prix"] = df["Prix"].astype(str) # Tout en texte d'abord
    df["Prix"] = df["Prix"].str.replace(',', '.', regex=False) # On remet des points pour Python
    # On nettoie les espaces invisibles (le vrai piège parfois)
    df["Prix"] = df["Prix"].str.replace(r'\s+', '', regex=True) 
    df["Prix"] = pd.to_numeric(df["Prix"], errors='coerce').fillna(0)
    
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