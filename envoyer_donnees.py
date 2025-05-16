import os
import subprocess


# === FONCTIONS ===
def envoyer_dossier_ssh(chemin_dossier_local, destination_ssh):
    """
    Envoie un dossier local vers un autre PC via SSH en utilisant scp.

    :param chemin_dossier_local: Chemin du dossier à envoyer (ex: /home/user/mon_dossier)
    :param destination_ssh: Cible SSH (ex: user@192.168.1.20:/home/user/destination)
    """
    chemin_dossier_local = os.path.expanduser(chemin_dossier_local)

    if not os.path.isdir(chemin_dossier_local):
        print(f"Le dossier spécifié n'existe pas : {chemin_dossier_local}")
        return

    try:
        print(f"Envoi de {chemin_dossier_local} vers {destination_ssh} ...")
        subprocess.run(["scp", "-r", chemin_dossier_local, destination_ssh], check=True)
        print("Envoi réussi.")
    except subprocess.CalledProcessError as e:
        print("Erreur lors de l'envoi :", e)


# === EXÉCUTION ===
if __name__ == "__main__":
    envoyer_dossier_ssh("~/Bureau/INFO/Etudes Pratiques/BACKUP", "inuss@10.9.31.241:/home/inuss/Bureau/INFO")
