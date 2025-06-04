import json
import shutil
from datetime import datetime
import os
import paramiko
import stat
import nats
import asyncio

def handle(event, context):

    def copier_dossier(source_dir, destination_dir):
        '''
        Crée une copie du dossier source vers destination 
            - source_dir : Chemin du dossier source 
            - destination_dir : Chemin de la destination de la copie 
        '''
        shutil.copytree(source_dir, destination_dir,dirs_exist_ok=True)

    def clean_folder(source):
        '''
        Suppression des fichiers du dossier
            - source : chemin d'accès au dossier
        '''
        source = os.path.expanduser(source)
        for fichier in os.listdir(source):  # Parcours tous les fichiers du dossier
            chemin_fichier = os.path.join(source, fichier)
            
            # Supprime tous les fichiers
            try:
                os.remove(chemin_fichier)  # Supprime le fichier
                print(f"Image supprimée : {chemin_fichier}")
            except Exception as e:
                print(f"Erreur lors de la suppression de {chemin_fichier} : {e}")


    def clean_json(fichier_json):
        '''
        Réinitialise le fichier JSON
            - fichier_json : chemin d'accès du fichier
        '''
        with open(fichier_json, 'w', encoding='utf-8') as f:
            json.dump([], f)
        print("Fichier réinitialisé")

    def simplifier_chemins(fichier_json):
        fichier_json = os.path.expanduser(fichier_json)

        with open(fichier_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        home_dir = os.path.expanduser('~') 

        for item in data:
            if item["image"].startswith(home_dir):
                item["image"] = item["image"].replace(home_dir, "~")

        with open(fichier_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print("Chemins simplifiés avec ~")

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

    def tri(source_folder, intervalle_secondes=15):
        '''
        ETAPE 1 : Crée une copie du dossier contenant les images et le fichier JSON
        ETAPE 2 : Supprime les images du dossier images principal et nettoie le fichier JSON
        ETAPE 3 : Ouvre la copie du fichier JSON
        ETAPE 4 : Tri les éléments du fichier en fonction de l'heure (ordre croissant)
        ETAPE 5 : Vérifie qu'il n'y a d'entrées du tableau JSON prises dans le même intervalle ou qui ne sont pas des animaux 
        ETAPE 6 : Met à jour le fichier JSON sans les doublons
            - source_folder : chemin du dossier principal
            - intervalle_secondes : fixé initialement à 15 secondes (pas obligatoire)
        '''
        animals = ["bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"]

        source_folder =  os.path.expanduser(source_folder)

        destination_folder = os.path.expanduser("/tmp/backup/")
        fichier_json = os.path.join(destination_folder, "detection_list.json")
        #fichierFinal_json = os.path.join(source_folder, "detection_list.json")

        # ETAPE 1 - Recopie du dossier
        copier_dossier(source_folder,destination_folder)

        # ETAPE 2 - Nettoyage
        clean_folder(os.path.join(source_folder, "images"))
        clean_json(os.path.join(source_folder, "detection_list.json"))
        modifier_chemin_image(destination_folder,fichier_json)

        # ETAPE 3 - Ouverture du fichier json en mode lecture
        with open(fichier_json, 'r', encoding='utf-8') as f:
            print("Ouverture du fichier JSON")
            data = json.load(f)

        # ETAPE 4 - Trier les éléments par heure
        sorted_data= sorted(data, key=lambda x: datetime.strptime(x["heure"], "%Y-%m-%d %H:%M:%S"))

        resultats = []
        images_suppression = []
        dernieres_heures_par_animal = {}

        # ETAPE 5 - Vérification
        for item in sorted_data:
            heure = datetime.strptime(item["heure"], "%Y-%m-%d %H:%M:%S")
            animal = item["animal"]
            
            if not ((animal not in dernieres_heures_par_animal or (heure - dernieres_heures_par_animal[animal]).total_seconds() >= intervalle_secondes) and animal in animals):
                images_suppression.append(item["image"])
            
            dernieres_heures_par_animal[animal] = heure

        for item in sorted_data:
            if item["image"] not in images_suppression:
                resultats.append(item)
            
        for img in images_suppression:
            try :
                image_path = os.path.expanduser(img)
                os.remove(image_path)  # Supprime l'image
                print(f"Image supprimée : {img}")
            except Exception as e:
                print(f"Erreur lors de la suppression de {img} : {e}")

        # ETAPE 6 - Écriture dans le fichier JSON
        with open(fichier_json, 'w', encoding='utf-8') as f:
            json.dump(resultats, f, indent=4, ensure_ascii=False)

        print(f"\n{len(data) - len(resultats)} détection(s) supprimée(s).")


    def is_directory(sftp, path):
        try:
            return stat.S_ISDIR(sftp.stat(path).st_mode)
        except IOError:
            return False

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

    def download_remote_folder_from_pi():
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

        remote_folder = "/home/fox/biolens/pictures"
        local_folder = "/tmp/pictures"

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

    def delete_remote_folder_via_sftp():
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

        folder_path="/home/fox/biolens/pictures"

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, key_filename=key_path)
        #ssh.connect(host, port=port, username=username, password=password)
        sftp = ssh.open_sftp()

        delete_remote_folder(sftp, folder_path)

        sftp.close()
        ssh.close()

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
        remote_folder="/home/fox/biolens/storage/images"

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

    async def send_yolo():
        # Connect to NATS!
        nc = await nats.connect(servers=["nats://100.78.231.17:4222"])

        # Publish a message to 'foo'
        await nc.publish("send", b"send files")

        # Make sure all published messages have reached the server
        await nc.flush()
        #print(f"Message envoyé : send files")

        # Close NATS connection
        await nc.close()


    download_remote_folder_from_pi()
    tri("/tmp/pictures/")
    simplifier_chemins("/tmp/backup/detection_list.json")
    delete_remote_folder_via_sftp()
    send_file_to_pi("/tmp/pictures/detection_list.json", "/home/fox/biolens/pictures/detection_list.json")
    send_file_to_pi("/tmp/backup/detection_list.json", "/home/fox/biolens/storage/detection_list.json")
    send_images_via_sftp()
    asyncio.run(send_yolo())

    return {
        "statusCode": 200,
        "body": "Tri effectué avec succès !"
    }
