import os
import time
import shutil
import subprocess
from datetime import datetime, timedelta

# === CONFIGURATION ===
DOSSIER_PHOTOS = "/home/amaury/Documents/Etudes Pratique/Local_to_Cloud/Dossier_Envoie/photos"
FICHIER_JSON = "/home/amaury/Documents/Etudes Pratique/Local_to_Cloud/Dossier_Envoie/detection_list2.json"
DOSSIER_TEMP = "/home/amaury/Documents/Etudes Pratique/Local_to_Cloud/Dossier_Temporaire"
DESTINATION = "/home/amaury/Documents/Etudes Pratique/Local_to_Cloud/Dossier_Reception"
FICHIER_TIMESTAMP = "/home/amaury/Documents/Etudes Pratique/Local_to_Cloud/Dossier_Envoie/dernier_envoie.txt"
INTERVALLE_MAX = timedelta(seconds=20) # minutes=1
NB_PHOTOS_MAX = 3

# === FONCTIONS ===
def lire_dernier_envoi():
    if os.path.exists(FICHIER_TIMESTAMP):
        with open(FICHIER_TIMESTAMP, 'r') as f:
            try:
                return datetime.fromisoformat(f.read().strip())
            except ValueError:
                pass
    return datetime.min

def enregistrer_dernier_envoi():
    with open(FICHIER_TIMESTAMP, 'w') as f:
        f.write(datetime.now().isoformat())

def envoyer_si_conditions_remplies():
    maintenant = datetime.now()
    dernier = lire_dernier_envoi()
    photos = [f for f in os.listdir(DOSSIER_PHOTOS) if f.lower().endswith(('.jpg', '.png'))]

    condition_photos = len(photos) >= NB_PHOTOS_MAX
    condition_temps = (maintenant - dernier) >= INTERVALLE_MAX

    if condition_photos or condition_temps:
        print(f"[{maintenant}] Déclenchement de l'envoi...")
        os.makedirs(DOSSIER_TEMP, exist_ok=True)

        # Copier jusqu'à 10 photos
        photos_a_envoyer = photos[:NB_PHOTOS_MAX]
        # Copier tout le dossier photos
        shutil.copytree(DOSSIER_PHOTOS, os.path.join(DOSSIER_TEMP, "photos"), dirs_exist_ok=True)


        # Copier le fichier JSON
        if os.path.exists(FICHIER_JSON):
            shutil.copy(FICHIER_JSON, DOSSIER_TEMP)

        # Envoi via SCP
        try:
            # subprocess.run(["scp", "-r", DOSSIER_TEMP, DESTINATION], check=True)
            shutil.copytree(DOSSIER_TEMP, DESTINATION, dirs_exist_ok=True)
            print("✅ Envoi réussi.")
        except subprocess.CalledProcessError:
            print("❌ Erreur lors de l'envoi.")
            return

        # Supprimer les photos envoyées
        for photo in photos_a_envoyer:
            os.remove(os.path.join(DOSSIER_PHOTOS, photo))
        enregistrer_dernier_envoi()
        shutil.rmtree(DOSSIER_TEMP)
    else:
        print(f"[{maintenant}] Pas encore le moment d'envoyer.")

# === EXÉCUTION ===
if __name__ == "__main__":
    envoyer_si_conditions_remplies()
