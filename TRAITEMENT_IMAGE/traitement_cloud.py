import cv2
from ultralytics import YOLO
import json
import os
from tqdm import tqdm
from collections import defaultdict

#Changer les chemins des fichiers
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


    # Charger le modèle YOLO enrichi
    model = YOLO("yolov8l.pt")

    # Dossier contenant les images
    image_dir = "test/images"
    # Fichier JSON à mettre à jour
    json_path = "test/detection_list.json"

    # Charger l'ancien fichier JSON pour récupérer les chemins et heures
    with open(json_path, "r") as f:
        old_data = json.load(f)

    # Créer un mapping image -> heure pour conserver l'heure de chaque image
    image_info_map = defaultdict(list)
    for entry in old_data:
        image_info_map[entry["image"]].append(entry.get("heure", ""))  # heure est facultative

    # Nouvelle liste pour les détections mises à jour
    new_detection_data = []

    # Parcourir les images
    for filename in tqdm(os.listdir(image_dir)):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(image_dir, filename)

            if image_path not in image_info_map:
                print(f"Image non présente dans l'ancien JSON : {image_path}")
                continue

            image = cv2.imread(image_path)
            if image is None:
                print(f"Erreur lecture image : {image_path}")
                continue

            # Exécuter YOLO sur l'image
            results = model(image)
            annotated_image = results[0].plot()  # Pour l'affichge de l'image annotée

            # Obtenir les classes détectées et leur certitude
            detections = results[0].boxes

            if detections is not None and len(detections.cls) > 0:
                class_indices = detections.cls.int().tolist()
                confidences = detections.conf.tolist()

                # Association des noms de classes avec les certitudes
                detection_counts = defaultdict(list)
                for idx, conf in zip(class_indices, confidences):
                    class_name = model.names[idx]
                    detection_counts[class_name].append(conf)

                # Ajouter les résultats à la liste des détections
                for class_name, conf_list in detection_counts.items():
                    count = len(conf_list)
                    avg_conf = sum(conf_list) / count * 100

                    new_detection_data.append({
                        "animal": class_name,
                        "effectif": count,
                        "certitude": f"{avg_conf:.2f}%",
                        "image": image_path,
                        "heure": image_info_map[image_path][0]  # garder la première heure trouvée
                    })

    # Sauvegarder le nouveau JSON
    with open(json_path, "w") as f:
        json.dump(new_detection_data, f, indent=4)

    print("\nFichier JSON mis à jour avec les nouvelles détections YOLO.")



if __name__ == '__main__':
    modifier_chemin_image("~/Bureau/INFO/Etudes Pratiques/", "~/Bureau/INFO/Etudes Pratiques/detection_list.json")
