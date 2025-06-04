import sqlite3
import json
import sys
import os
from datetime import datetime as dt
import discord
import os
from dotenv import load_dotenv
import asyncio
import paramiko
import nats
import stat



def handle(event, context):

    DISCORD_TOKEN="MTM2MTMxNDQxMjg4MjgyMTI3Ng.GhZ9-L.kFAqM0cEUUheEBYPa7yAcrZ0m4KpkE0Z-MSanI"
    DISCORD_CHANNEL_ID=1361321354602873092

    load_dotenv()

    """Création de la base de données et des tables si elles n'existent pas déjà."""
    def create_database():
        conn = sqlite3.connect("/tmp/bdd/detections.db")
        cursor = conn.cursor()

        # Table photo (ID photo, Date, Heure, Nb total d'animaux, chemin de l'image)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photo (
                IDphoto INTEGER PRIMARY KEY AUTOINCREMENT,
                Date TEXT,
                Heure TEXT,
                Nombre_total_animaux INTEGER,
                Chemin_image TEXT
            )
        ''')

        # Table animalDetecte (ID, ID phot, Classe animal, Nmbre)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS animalDetecte (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                IDphoto INTEGER,
                Classe_animal TEXT,
                Nombre INTEGER,
                FOREIGN KEY (IDphoto) REFERENCES photo (IDphoto)
            )
        ''')

        conn.commit()
        conn.close()

    """Chargement des données de détection depuis un fichier JSON."""
    def load_detections_from_json(file_path):
        with open(file_path, "r") as f:
            return json.load(f)

    """Insertion les données dans les tables photo et animalDetecté."""
    def insert_data(detection_list):
        if not detection_list:
            print("Aucune détection à insérer.")
            return

        # Regrouper les détections par image
        grouped_by_image = {}
        for detection in detection_list:
            image_path = detection["image"]
            if image_path not in grouped_by_image:
                grouped_by_image[image_path] = []
            grouped_by_image[image_path].append(detection)

        conn = sqlite3.connect("/tmp/bdd/detections.db")
        cursor = conn.cursor()

        for image_path, detections in grouped_by_image.items():
            # Extraire la date et l’heure de la première détection
            heure_complete = detections[0]["heure"]
            date_str, heure_str = heure_complete.split(" ")
            total_animaux = sum([det["effectif"] for det in detections])

            # Insérer dans la table photo avec le chemin de l’image
            cursor.execute('''
                INSERT INTO photo (Date, Heure, Nombre_total_animaux, Chemin_image)
                VALUES (?, ?, ?, ?)
            ''', (date_str, heure_str, total_animaux, image_path))
            IDphoto = cursor.lastrowid

            # Insérer chaque détection dans la table animalDetecte
            for det in detections:
                cursor.execute('''
                    INSERT INTO animalDetecte (IDphoto, Classe_animal, Nombre)
                    VALUES (?, ?, ?)
                ''', (
                    IDphoto,
                    det["animal"],
                    det["effectif"]
                ))

        conn.commit()
        conn.close()
        print("Données insérées avec succès dans les tables photo et animalDetecte.")

    def download_remote_folder_from_serveur(remote_folder, local_folder):
        host = "100.108.186.115"
        port = 22
        username = "serveur"
        #password = "foxinsa"

        secret_path = "/var/openfaas/secrets/ssh-private-key"
        if not os.path.exists(secret_path):
            raise Exception(f"SSH private key secret not found at {secret_path}")

        # Lire la clé privée depuis le secret
        with open(secret_path, "r") as f:
            private_key_data = f.read()

        # Écrire la clé privée dans un fichier temporaire avec les bonnes permissions
        key_path = "/tmp/pi_key"
        with open(key_path, "w") as f:
            f.write(private_key_data)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600

        #remote_folder = "/home/serveur/biolens/data"
        #local_folder = "/tmp/pictures"

        # Connexion
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, key_filename=key_path)

        sftp = ssh.open_sftp()
        download_folder(sftp, remote_folder, local_folder)

        sftp.close()
        ssh.close()

    def download_folder(sftp, remote_path, local_path):
        os.makedirs(local_path, exist_ok=True)

        for item in sftp.listdir_attr(remote_path):
            #print("Item :", item)
            remote_item = remote_path + "/" + item.filename
            local_item = os.path.join(local_path, item.filename)

            if stat.S_ISDIR(item.st_mode):
                # Récursion pour les sous-dossiers
                download_folder(sftp, remote_item, local_item)
            else:
                sftp.get(remote_item, local_item)
                print(f"Téléchargé : {remote_item} → {local_item}")

    def send_file_to_pi(local_path, remote_path):
        host = "100.108.186.115"
        port = 22
        username = "serveur"
        #password = "foxinsa"

        secret_path = "/var/openfaas/secrets/ssh-private-key"
        if not os.path.exists(secret_path):
            raise Exception(f"SSH private key secret not found at {secret_path}")

        # Lire la clé privée depuis le secret
        with open(secret_path, "r") as f:
            private_key_data = f.read()

        # Écrire la clé privée dans un fichier temporaire avec les bonnes permissions
        key_path = "/tmp/pi_key"
        with open(key_path, "w") as f:
            f.write(private_key_data)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600

        #local_path="/tmp/pictures/detection_list.json"
        #remote_path="/home/fox/biolens/pictures/detection_list.json"
        
        # Connexion SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, key_filename=key_path)

        # SFTP
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)
        print(f"Fichier envoyé : {local_path} → {remote_path}")

        sftp.close()
        ssh.close()

    def delete_remote_folder_via_sftp():
        host = "100.108.186.115"
        port = 22
        username = "serveur"
        #password = "foxinsa"

        secret_path = "/var/openfaas/secrets/ssh-private-key"
        if not os.path.exists(secret_path):
            raise Exception(f"SSH private key secret not found at {secret_path}")

        # Lire la clé privée depuis le secret
        with open(secret_path, "r") as f:
            private_key_data = f.read()

        # Écrire la clé privée dans un fichier temporaire avec les bonnes permissions
        key_path = "/tmp/pi_key"
        with open(key_path, "w") as f:
            f.write(private_key_data)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600

        folder_path="/home/serveur/biolens/data"

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, key_filename=key_path)
        #ssh.connect(host, port=port, username=username, password=password)
        sftp = ssh.open_sftp()

        delete_remote_folder(sftp, folder_path)

        sftp.close()
        ssh.close()

    def delete_remote_folder(sftp, path):
        print(f"Suppression du dossier : {path}")
        for item in sftp.listdir_attr(path):
            print("Item :", item.filename)
            item_path = f"{path}/{item.filename}"
            if stat.S_ISDIR(item.st_mode):
                # Dossier → récursion
                delete_remote_folder(sftp, item_path)
                #sftp.rmdir(item_path)
                print(f"Dossier supprimé : {item_path}")
            else:
                # Fichier
                sftp.remove(item_path)
                print(f"Fichier supprimé : {item_path}")

    def modifier_chemin_image(destination, fichier_json):
        destination = os.path.expanduser(destination+"images/")
        fichier_json = os.path.expanduser(fichier_json)

        home_dir = os.path.expanduser('~')

        with open(fichier_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for item in data:

            nom_fichier = os.path.basename(item["image"])
            item["image"] = os.path.join(destination, nom_fichier)
            if item["image"].startswith(home_dir):
                item["image"] = item["image"].replace(home_dir, "~")
        
        with open(fichier_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print("Chemins modifiés")

    """Fonction pour envoyer un message Discord"""
    async def send_discord_notification(message):
        bot = discord.Client(intents=discord.Intents.all())

        @bot.event
        async def on_ready():
            print("Bot connecté à Discord.")
            channel = bot.get_channel(int(DISCORD_CHANNEL_ID))
            if channel:
                await channel.send(message)
            else:
                print("Salon Discord introuvable.")
            await bot.close()

        await bot.start(DISCORD_TOKEN)

    def main():

        detection_file = "/tmp/pictures/detection_list.json"
        detection_file = os.path.expanduser(detection_file)
        if not os.path.exists(detection_file):
            print(f"Erreur : Le fichier {detection_file} n'existe pas.")
            return ["Erreur : Le fichier de détection n'existe pas."]

        detection_list = []
        try:
            detection_list = load_detections_from_json(detection_file)
            create_database()
            insert_data(detection_list)
        except Exception as e:
            print(f"Erreur lors du traitement du fichier JSON : {e}")
            return [f"Erreur lors du traitement du fichier JSON. {e}"]

        # Lancer l'envoi du message Discord si des données ont été insérées
        total_animaux = sum([det["effectif"] for det in detection_list])
        total_photos = len(set(det["image"] for det in detection_list))
        current_date_and_time = dt.now()
        if total_animaux > 0:
            message = f"[{current_date_and_time}] Mise à jour de la base de données : {total_photos} photos ont été prises et {total_animaux} animaux ont été détéctés ."
            asyncio.run(send_discord_notification(message))
        else:
            print("Aucune donnée insérée, aucun message Discord envoyé.")

        return detection_list
    
    def send_images_via_sftp():
        """
        Envoie toutes les images d'un dossier local vers un dossier distant via SFTP.

        Args:
            host (str): Adresse IP ou hostname du serveur SSH.
            port (int): Port SSH (souvent 22).
            username (str): Nom d'utilisateur SSH.
            key_path (str): Chemin vers la clé privée SSH.
            local_folder (str): Dossier local contenant les images.
            remote_folder (str): Dossier distant où envoyer les images.
        """

        host = "100.108.186.115"
        port = 22
        username = "serveur"
        #password = "foxinsa"

        secret_path = "/var/openfaas/secrets/ssh-private-key"
        if not os.path.exists(secret_path):
            raise Exception(f"SSH private key secret not found at {secret_path}")

        # Lire la clé privée depuis le secret
        with open(secret_path, "r") as f:
            private_key_data = f.read()

        # Écrire la clé privée dans un fichier temporaire avec les bonnes permissions
        key_path = "/tmp/pi_key"
        with open(key_path, "w") as f:
            f.write(private_key_data)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600

        local_folder="/tmp/pictures/images"
        remote_folder="/home/serveur/biolens/bdd/images"

        # Extensions des images à transférer
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}

        # Connexion SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, key_filename=key_path)

        # Connexion SFTP
        sftp = ssh.open_sftp()

        # Crée le dossier distant s'il n'existe pas
        try:
            sftp.stat(remote_folder)
        except FileNotFoundError:
            sftp.mkdir(remote_folder)

        # Parcours des fichiers dans le dossier local
        for filename in os.listdir(local_folder):
            if any(filename.lower().endswith(ext) for ext in image_extensions):
                local_path = os.path.join(local_folder, filename)
                remote_path = remote_folder.rstrip('/') + '/' + filename
                print(f"Upload {local_path} -> {remote_path}")
                sftp.put(local_path, remote_path)

        # Fermer les connexions
        sftp.close()
        ssh.close()

    download_remote_folder_from_serveur("/home/serveur/biolens/data", "/tmp/pictures")
    download_remote_folder_from_serveur("/home/serveur/biolens/bdd", "/tmp/bdd")
    modifier_chemin_image("/home/mathys/Etude_Pratique/biolens/bdd/", "/tmp/pictures/detection_list.json")
    res = main()
    send_images_via_sftp()
    delete_remote_folder_via_sftp()
    send_file_to_pi("/tmp/pictures/detection_list.json", "/home/serveur/biolens/data/detection_list.json")
    send_file_to_pi("/tmp/bdd/detections.db", "/home/serveur/biolens/bdd/detections.db")


    return {
        "statusCode": 200,
        "body": "Data saved and Discord notification sent successfully. Resultat : " + str(res)
    }
