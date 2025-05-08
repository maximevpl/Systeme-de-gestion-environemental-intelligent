import json
import shutil
from datetime import datetime
import os

def copier_dossier(source_dir, destination_dir):
    '''
    Crée une copie du dossier source vers destination 
        - source_dir : Chemin du dossier source 
        - destination_dir : Chemin de la destination de la copie 
    '''
    shutil.copytree(source_dir, destination_dir,dirs_exist_ok=True)

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


def sending_failed(source, destination):
    # Étape 1 - copier toutes les images
    copier_dossier(os.path.expanduser(os.path.join(source, "images")), os.path.expanduser(os.path.join(destination, "images")))

    # Étape 2 - fusionner les fichiers JSON
    fusionner_json(os.path.join(destination, "detection_list.json"), os.path.join(source, "detection_list.json"))

    # Étape 3 - supprimer le dossier source
    clean_dir(os.path.expanduser(source))


def successfull_sending(source):
    # Étape - supprimer le dossier source
    clean_dir(os.path.expanduser(source))


if __name__ == '__main__':
    #fusionner_json("~/Bureau/INFO/Etudes Pratiques/TRI/detection_list.json","~/Bureau/INFO/Etudes Pratiques/TRI/detection_list2.json")
    sending_failed("~/Bureau/INFO/Etudes Pratiques/BACKUP","~/Bureau/INFO/Etudes Pratiques/TRI")