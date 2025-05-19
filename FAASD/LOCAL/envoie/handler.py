import os
import subprocess
import json
import shutil
from datetime import datetime
import stat
import paramiko


def handle(event, context):

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

    def download_remote_folder_from_pi(remote_folder, local_folder):
        host = "100.78.231.17"
        port = 22
        username = "fox"
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

        #remote_folder = "/home/fox/biolens/pictures"
        #local_folder = "/tmp/pictures"

        # Connexion
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, key_filename=key_path)

        sftp = ssh.open_sftp()
        download_folder(sftp, remote_folder, local_folder)

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

        # Supprimer le dossier racine après son contenu
        #sftp.rmdir(path)
        print(f"Dossier racine supprimé : {path}")

    def delete_remote_folder_via_sftp(folder_path):
        host = "100.78.231.17"
        port = 22
        username = "fox"
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

        #folder_path="/home/fox/biolens/storage"

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, key_filename=key_path)
        #ssh.connect(host, port=port, username=username, password=password)
        sftp = ssh.open_sftp()

        delete_remote_folder(sftp, folder_path)

        sftp.close()
        ssh.close()

    def copier_dossier(source_dir, destination_dir):
        '''
        Crée une copie du dossier source vers destination 
            - source_dir : Chemin du dossier source 
            - destination_dir : Chemin de la destination de la copie 
        '''
        shutil.copytree(source_dir, destination_dir,dirs_exist_ok=True)

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

        host = "100.78.231.17"
        port = 22
        username = "fox"
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

        local_folder="/tmp/backup/images"
        remote_folder="/home/fox/biolens/pictures/images"

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

    def clean_dir(source):
        '''
        Vide le contenu du dossier sans supprimer le dossier lui-même.
            - source : chemin d'accès au dossier
        '''
        source = os.path.expanduser(source)

        for item in os.listdir(source):
            item_path = os.path.join(source, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)


    def fusionner_json(fichier_src, fichier_ajout):
        """
        Fusionne deux fichiers JSON.
            - fichier_src: Chemin vers le fichier JSON source
            - fichier_ajout: Chemin vers le fichier JSON à ajouter
        """
        fichier_src = os.path.expanduser(fichier_src)
        fichier_ajout = os.path.expanduser(fichier_ajout)

        with open(fichier_src, "r", encoding="utf-8") as f1:
            data_src = json.load(f1)

        with open(fichier_ajout, "r", encoding="utf-8") as f2:
            data_ajout = json.load(f2)

        fusion = data_src + data_ajout

        with open(fichier_src, "w", encoding="utf-8") as fout:
            json.dump(fusion, fout, ensure_ascii=False, indent=4)

        print(f"Fusion terminée : {len(fusion)} éléments écrits dans {fichier_src}")
    
    def send_file_to_pi(local_path, remote_path):
        host = "100.78.231.17"
        port = 22
        username = "fox"
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

    def save_detections_to_json(resultat, com):
        file_path = "/tmp/logs/logs.json"

        # Si le fichier JSON existe déjà, charger les données existantes
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                existing_data = json.load(f)
        else:
            existing_data = []

        log = {
                "resultat": resultat,
                "heure": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "commentaire": com
        }

        # Ajouter le nouveau log aux anciennes données
        existing_data.append(log)

        # Sauvegarder la liste mise à jour dans le fichier JSON
        with open(file_path, "w") as f:
            json.dump(existing_data, f, indent=4)


    def sending_failed(source, destination, error):
        # Étape 1 - copier toutes les images
        send_images_via_sftp()
        #copier_dossier(os.path.expanduser(os.path.join(source, "images")), os.path.expanduser(os.path.join(destination, "images")))

        # Étape 2 - fusionner les fichiers JSON
        fusionner_json(os.path.join(destination, "detection_list.json"), os.path.join(source, "detection_list.json"))
        send_file_to_pi("/tmp/backup/detection_list.json", "/home/fox/biolens/pictures/detection_list.json")

        # Etape 2bis - sauvegarde des logs
        save_detections_to_json("Failed", error)
        send_file_to_pi("/tmp/logs/logs.json", "/home/fox/biolens/logs/logs.json")

        # Étape 3 - supprimer le dossier source
        delete_remote_folder_via_sftp("/home/fox/biolens/storage")
        #clean_dir(os.path.expanduser(source))


    def successfull_sending():
        # Étape - supprimer le dossier source
        #clean_dir(os.path.expanduser(source))
        delete_remote_folder_via_sftp("/home/fox/biolens/storage")

        # Etape 2 - sauvegarde des logs
        save_detections_to_json("Success", "Envoi des images et du fichier JSON reussi !")
        send_file_to_pi("/tmp/logs/logs.json", "/home/fox/biolens/logs/logs.json")



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
            #subprocess.run(["scp", "-r", chemin_dossier_local, destination_ssh], check=True)
            send_folder_via_sftp("100.94.14.127", "mathys", chemin_dossier_local, destination_ssh)
            successfull_sending()
            print("Envoi réussi.")
        except subprocess.CalledProcessError as e:
            sending_failed("/tmp/backup","/tmp/pictures", e)
            print("Erreur lors de l'envoi :", e)

    def send_folder_via_sftp(host, username, local_folder, remote_folder):
        """
        Envoie récursivement le contenu d'un dossier local vers un dossier distant via SFTP.
        Utilise une clé SSH stockée dans un secret OpenFaaS.
        """

        #host = "100.94.14.127" #Ip vers où envoyer les données (ip du serveur)
        port = 22
        #username = "mathys"

        secret_path = "/var/openfaas/secrets/ssh-private-key"
        if not os.path.exists(secret_path):
            raise Exception(f"SSH private key secret not found at {secret_path}")

        # Lire et écrire la clé temporairement
        key_path = "/tmp/pi_key"
        with open(secret_path, "r") as f:
            private_key_data = f.read()
        with open(key_path, "w") as f:
            f.write(private_key_data)
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)

        #local_folder = "/tmp/backup"
        #remote_folder = "/home/mathys/Etude_Pratique/biolens/serveur"

        # Connexion SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, key_filename=key_path)

        # Connexion SFTP
        sftp = ssh.open_sftp()

        def remote_exists(path):
            try:
                sftp.stat(path)
                return True
            except FileNotFoundError:
                return False

        def ensure_remote_dir(path):
            """
            Crée récursivement les dossiers distants.
            """
            parts = path.strip("/").split("/")
            current_path = ""
            for part in parts:
                current_path += "/" + part
                if not remote_exists(current_path):
                    sftp.mkdir(current_path)

        def upload_recursive(local_path, remote_path):
            """
            Envoie récursivement les fichiers et dossiers.
            """
            if os.path.isdir(local_path):
                ensure_remote_dir(remote_path)
                for entry in os.listdir(local_path):
                    entry_local = os.path.join(local_path, entry)
                    entry_remote = os.path.join(remote_path, entry)
                    upload_recursive(entry_local, entry_remote)
            else:
                print(f"Upload {local_path} -> {remote_path}")
                sftp.put(local_path, remote_path)

        # Lancer l'envoi récursif
        upload_recursive(local_folder, remote_folder)

        sftp.close()
        ssh.close()


    # === EXÉCUTION ===
    download_remote_folder_from_pi("/home/fox/biolens/pictures", "/tmp/pictures")
    download_remote_folder_from_pi("/home/fox/biolens/storage", "/tmp/backup")
    download_remote_folder_from_pi("/home/fox/biolens/logs", "/tmp/logs")
    envoyer_dossier_ssh("/tmp/backup", "/home/mathys/Etude_Pratique/biolens/serveur")
    clean_dir("/tmp/backup")
    clean_dir("/tmp/pictures")
    clean_dir("/tmp/logs")


    return {
        "statusCode": 200,
        "body": "Envoie effectué !"
    }
