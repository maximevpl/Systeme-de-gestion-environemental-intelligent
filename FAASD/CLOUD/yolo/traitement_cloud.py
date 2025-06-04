import cv2
from ultralytics import YOLO
import json
import os
from tqdm import tqdm
from collections import defaultdict
import nats as NATS
import asyncio

#Changer les chemins des fichiers
def process_images(destination, fichier_json):
    destination = os.path.expanduser(destination)
    fichier_json = os.path.expanduser(fichier_json)
    
    home_dir = os.path.expanduser('~')

    with open(fichier_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:

        nom_fichier = os.path.basename(item["image"])
        item["image"] = os.path.join(destination, nom_fichier)
        #if item["image"].startswith(home_dir):
        #    item["image"] = item["image"].replace(home_dir, "~")

    with open(fichier_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print("Chemins modifiés")


    # Charger le modèle YOLO enrichi
    model = YOLO("my_model.pt")

    # Dossier contenant les images
    image_dir = destination
    #image_dir = image_dir.replace(home_dir, "~")
    print(image_dir)
    # Fichier JSON à mettre à jour
    json_path = fichier_json
    print("variables init")
    # Charger l'ancien fichier JSON pour récupérer les chemins et heures
    with open(json_path, "r") as f:
        old_data = json.load(f)
    print("json ouvert")
    # Créer un mapping image -> heure pour conserver l'heure de chaque image
    image_info_map = defaultdict(list)
    for entry in old_data:
        image_info_map[entry["image"]].append(entry.get("heure", ""))  # heure est facultative

    # Nouvelle liste pour les détections mises à jour
    new_detection_data = []

    # Parcourir les images
    for filename in tqdm(os.listdir(image_dir)):
        #print("Fichier : ", filename)
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            image_path = os.path.join(image_dir, filename)

            if image_path not in image_info_map:
                #print(f"Image non présente dans l'ancien JSON : {image_path}")
                continue

            image = cv2.imread(image_path)
            if image is None:
                print(f"Erreur lecture image : {image_path}")
                continue

            # Exécuter YOLO sur l'image
            results = model(image)
            #print("resultats : ",results)
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
                    print("Add : ", class_name)

                    new_detection_data.append({
                        "animal": class_name,
                        "effectif": count,
                        "certitude": f"{avg_conf:.2f}%",
                        "image": image_path,
                        "heure": image_info_map[image_path][0]  # garder la première heure trouvée
                    })

    print(new_detection_data)
    # Sauvegarder le nouveau JSON
    with open(json_path, "w") as f:
        json.dump(new_detection_data, f, indent=4)

    print("\nFichier JSON mis à jour avec les nouvelles détections YOLO.")

    try:
        loop = asyncio.get_running_loop()
        # Lancer la coroutine sans l'attendre (non-bloquant)
        asyncio.create_task(send_yolo())
    except RuntimeError:
        # Si pas de boucle en cours : fallback
        asyncio.run(send_yolo())

async def receive_message_from_biolens():
    # Connect to NATS!
    nc = await NATS.connect(servers=["nats://127.0.0.1:4222"])

    # Receive messages on 'foo'
    sub = await nc.subscribe("yoloCloud")
    print("Attente de message sur le topic yoloCloud...")

    try:
        while True:
            msg = await sub.next_msg(timeout=None)
            print("Received:", msg)
            image_path = os.path.expanduser(msg.data.decode())
            #process_image(image_path)
            try:
                process_images("~/biolens/data/images/", "~/biolens/data/detection_list.json")
                #save_detections_to_json(detection_list)  # Sauvegarder la liste des détections dans un fichier JSON
                print("\nLes détections ont été sauvegardées dans /pictures/detection_list.json.")

            except Exception as e:
                print(f"Erreur lors du traitement de la photo : {e}")

    except asyncio.CancelledError:
        print("Arrêt du programme.")
    finally:
        await nc.close()

async def send_yolo():
    # Connect to NATS!
    nc = await NATS.connect(servers=["nats://100.108.186.115:4222"])

    # Publish a message to 'foo'
    await nc.publish("tri", b"start tri")

    # Make sure all published messages have reached the server
    await nc.flush()
    #print(f"Message envoyé : send files")

    # Close NATS connection
    await nc.close()

if __name__ == '__main__':
    asyncio.run(receive_message_from_biolens())
    
