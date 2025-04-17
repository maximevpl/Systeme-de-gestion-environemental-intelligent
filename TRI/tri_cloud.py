import json
from datetime import datetime
import os


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

    
def tri(fichier_json, intervalle_secondes=30):
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
            dernieres_heures_par_animal[animal] = heure
        else : 
            try :
                image_path = os.path.expanduser(item["image"])
                os.remove(image_path)
                print(f"Image supprimée : {item["image"]}")
            except Exception as e:
                print(f"Erreur lors de la suppression de {item["image"]} : {e}")
        
    # ETAPE 4 - Écriture dans le fichier JSON
    with open(fichier_json, 'w', encoding='utf-8') as f:
        json.dump(resultats, f, indent=4, ensure_ascii=False)

    print(f"\n{len(data) - len(resultats)} détection(s) supprimée(s).")




if __name__ == '__main__':
    # tri("/home/inuss/Bureau/INFO/Etudes Pratiques/tri/detection_list2.json", intervalle_secondes=30)
    tri("~/Bureau/INFO/Etudes Pratiques/tri/BACKUP/detection_list2.json")
