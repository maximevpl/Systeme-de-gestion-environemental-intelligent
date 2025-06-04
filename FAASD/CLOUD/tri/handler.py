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


    def tri(fichier_json, intervalle_secondes=15):
        '''
        ETAPE 1 : Ouvre la copie du fichier JSON
        ETAPE 2 : Tri les éléments du fichier en fonction de l'heure
        ETAPE 3 : Vérifie qu'il n'y a pas de doublons sinon supprime l'image correspondante
        ETAPE 4 : Met à jour le fichier JSON sans les doublons
            - fichier_json : chemin du fichier json
            - intervalle_secondes : fixé initialement à 30 secondes (pas obligatoire)
        '''

        # Permet l'interprétation de "~"
        fichier_json = os.path.expanduser(fichier_json) 

        # ETAPE 1 - Ouverture du fichier json
        with open(fichier_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # ETAPE 2 - Trier les éléments par heure
        data_triee = sorted(data, key=lambda x: datetime.strptime(x["heure"], "%Y-%m-%d %H:%M:%S"))

        resultats = []
        dernieres_heures_par_animal = {}

        # ETAPE 3 - Vérification
        for item in data_triee:
            heure = datetime.strptime(item["heure"], "%Y-%m-%d %H:%M:%S")
            animal = item["animal"]

            if animal not in dernieres_heures_par_animal or (heure - dernieres_heures_par_animal[animal]).total_seconds() >= intervalle_secondes:
                resultats.append(item)
            else : 
                try :
                    image_path = os.path.expanduser(item["image"])
                    os.remove(image_path)
                    print(f"Image supprimée : {item["image"]}")
                except Exception as e:
                    print(f"Erreur lors de la suppression de {item["image"]} : {e}")
            dernieres_heures_par_animal[animal] = heure
            
        # ETAPE 4 - Écriture dans le fichier JSON
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

    def download_remote_folder_from_serveur():
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

        remote_folder = "/home/serveur/biolens/data"
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
        remote_folder="/home/serveur/biolens/data/images"

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
        nc = await nats.connect(servers=["nats://100.108.186.115:4222"])

        # Publish a message to 'foo'
        await nc.publish("bdd", b"save results")

        # Make sure all published messages have reached the server
        await nc.flush()
        #print(f"Message envoyé : send files")

        # Close NATS connection
        await nc.close()

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


    download_remote_folder_from_serveur()
    modifier_chemin_image("/tmp/pictures/", "/tmp/pictures/detection_list.json")
    tri("/tmp/pictures/detection_list.json")
    modifier_chemin_image("/home/serveur/biolens/data/", "/tmp/pictures/detection_list.json")
    simplifier_chemins("/tmp/pictures/detection_list.json")
    delete_remote_folder_via_sftp()
    send_file_to_pi("/tmp/pictures/detection_list.json", "/home/serveur/biolens/data/detection_list.json")
    #send_file_to_pi("/tmp/backup/detection_list.json", "/home/serveur/biolens/storage/detection_list.json")
    #simplifier_chemins("/tmp/pictures/detection_list.json")
    send_images_via_sftp()
    clean_dir("/tmp/pictures")
    asyncio.run(send_yolo())

    return {
        "statusCode": 200,
        "body": "Tri effectué avec succès !"
    }
