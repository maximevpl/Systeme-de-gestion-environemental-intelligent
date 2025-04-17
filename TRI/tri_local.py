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
    shutil.copytree(source_dir, destination_dir)

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

def clean_dir(source):
    '''
    Supprime le dossier 
        - source : chemin d'accès au dossier
    '''
    source = os.path.expanduser(source)
    shutil.rmtree(source)

def clean_json(fichier_json):
    '''
    Réinitialise le fichier JSON
        - fichier_json : chemin d'accès du fichier
    '''
    with open(fichier_json, 'w', encoding='utf-8'):
        pass
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
    destination = os.path.expanduser(destination)
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



def tri(source_folder, intervalle_secondes=30):
    '''
    ETAPE 1 : Crée une copie du dossier contenant les images et le fichier JSON
    ETAPE 2 : Supprime les images du dossier images principal et nettoie le fichier JSON
    ETAPE 3 : Ouvre la copie du fichier JSON
    ETAPE 4 : Tri les éléments du fichier en fonction de l'heure
    ETAPE 5 : Vérifie qu'il n'y a d'entrées du tableau JSON prises dans le même intervalle  
    ETAPE 6 : Met à jour le fichier JSON sans les doublons
        - source_folder : chemin du dossier principal
        - intervalle_secondes : fixé initialement à 30 secondes (pas obligatoire)
    '''
    source_folder =  os.path.expanduser(source_folder)

    destination_folder = os.path.expanduser("~/Bureau/INFO/Etudes Pratiques/BACKUP")
    fichier_json = os.path.join(destination_folder, "detection_list2.json")

    # ETAPE 1 - Recopie du dossier
    copier_dossier(source_folder,destination_folder)

    # ETAPE 2 - Nettoyage
    clean_folder(os.path.join(source_folder, "images"))
    clean_json(os.path.join(source_folder, "detection_list2.json"))
    modifier_chemin_image(destination_folder,fichier_json)

    # ETAPE 3 - Ouverture du fichier json en mode lecture
    with open(fichier_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # ETAPE 4 - Trier les éléments par heure
    data_triee = sorted(data, key=lambda x: datetime.strptime(x["heure"], "%Y-%m-%d %H:%M:%S"))

    resultats = []
    derniere_heure  = None

    # ETAPE 5 - Vérification
    for item in data_triee:
        heure = datetime.strptime(item["heure"], "%Y-%m-%d %H:%M:%S")
        
        if derniere_heure is None or (heure - derniere_heure).total_seconds() >= intervalle_secondes:
            resultats.append(item)
            derniere_heure = heure
        else : 
            try :
                image_path = os.path.expanduser(item["image"])
                os.remove(image_path)  # Supprime l'image
                print(f"Image supprimée : {item["image"]}")
            except Exception as e:
                print(f"Erreur lors de la suppression de {item["image"]} : {e}")
        
    # ETAPE 6 - Écriture dans le fichier JSON
    with open(fichier_json, 'w', encoding='utf-8') as f:
        json.dump(resultats, f, indent=4, ensure_ascii=False)

    print(f"\n{len(data) - len(resultats)} détection(s) supprimée(s).")




if __name__ == '__main__':
    tri("~/Bureau/INFO/Etudes Pratiques/TRI")
    #simplifier_chemins("~/Bureau/INFO/Etudes Pratiques/TRI/detection_list.json")
    #clean_dir("~/Bureau/INFO/Etudes Pratiques/BACKUP")
