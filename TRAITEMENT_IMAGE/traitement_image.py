import cv2
from ultralytics import YOLO
from tkinter import Tk, filedialog
from collections import defaultdict
from datetime import datetime
import json
import sys
import subprocess
import os

# Charger le modèle YOLOv8
model = YOLO("yolov8l.pt")

# Liste pour stocker les résultats de détection
detection_list = []


''' Fonction pour traiter une image avec YOLO
et de récupérer les informations sur la détection '''
def process_image(image_path):
    # Charger l'image
    image = cv2.imread(image_path)
    if image is None:
        print("Erreur : Impossible de charger l'image.")
        return

    # Exécuter YOLO sur l'image
    results = model(image)
    annotated_image = results[0].plot() #Pour l'affichge de l'image annotée

    # Obtenir les classes détectées et leur certitude
    detections = results[0].boxes
    if detections is not None:
        class_indices = detections.cls.int().tolist()  # Indices des classes
        confidences = detections.conf.tolist()  # Certitudes associées

        # Association des noms de classes avec les certitudes
        detection_data = defaultdict(list)
        for idx, confidence in zip(class_indices, confidences):
            class_name = model.names[idx]
            detection_data[class_name].append(confidence)

        # Ajouter les résultats à la liste des détections
        detection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for class_name, confidence_list in detection_data.items():
            count = len(confidence_list)
            avg_confidence = sum(confidence_list) / count * 100  # Moyenne en pourcentage
            detection_list.append({
                "animal": class_name,
                "effectif": count,
                "certitude": f"{avg_confidence:.2f}%",
                "heure": detection_time,
                "image": image_path
            })
            print(f"- {class_name} : {count} détection(s), certitude moyenne : {avg_confidence:.2f}%")

    # Afficher l'image annotée
    # cv2.imshow("Image Annotée", annotated_image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()


# Menu pour choisir l'image en mode manuel
def choose_file():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Sélectionnez une image",
        filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp")]
    )
    return file_path


''' Fonction qui permet de sauvegarder les informations issues 
du traitement (detection_list) dans un fichier JSON'''
def save_detections_to_json(detection_list):
    file_path = "detection_list.json"

    # Si le fichier JSON existe déjà, charger les données existantes
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    # Ajouter les nouvelles détections aux anciennes données
    existing_data.extend(detection_list)

    # Sauvegarder la liste mise à jour dans le fichier JSON
    with open(file_path, "w") as f:
        json.dump(existing_data, f, indent=4)


def main():
    #open("list_detection_temp/detection_list.json", "w").write("[]") #Vider le fichier JSON manuellement

    if len(sys.argv) < 2:
        print("Erreur : Il faut passer une photo en paramètre.")
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"Erreur : Le fichier {image_path} n'existe pas.")
        sys.exit(1)

    try:
        process_image(image_path)
        save_detections_to_json(detection_list)  # Sauvegarder la liste des détections dans un fichier JSON
        print("\nLes détections ont été sauvegardées dans detection_list.json.")
    except Exception as e:
        print(f"Erreur lors du traitement de la photo : {e}")
        sys.exit(1)



if __name__ == "__main__":
    main()

''' Pour lancer le script en mode manuel : 
# Lancer la sélection et le traitement
image_path = choose_file()
if image_path:
    process_image(image_path)
    save_detections_to_json(detection_list)  # Sauvegarder la liste des détections dans un fichier JSON
    print("\nLes détections ont été sauvegardées dans detection_list.json.")

    # Lancer le deuxième script en passant le fichier JSON comme argument
    subprocess.run(["python", "stockage_BD_V2.py", "list_detection_temp/detection_list.json"])
else:
    print("Aucun fichier sélectionné.")
'''

