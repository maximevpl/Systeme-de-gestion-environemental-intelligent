import sqlite3
import json
import sys
import os
from datetime import datetime as dt
import discord
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

"""Création de la base de données et des tables si elles n'existent pas déjà."""
def create_database():
    conn = sqlite3.connect("detections.db")
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

    conn = sqlite3.connect("detections.db")
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


"""Fonction pour envoyer un message Discord"""
async def send_discord_notification(message):
    bot = discord.Client(intents=discord.Intents.all())

    @bot.event
    async def on_ready():
        print("Bot connecté à Discord.")
        channel = bot.get_channel(int(os.getenv('DISCORD_CHANNEL_ID')))
        if channel:
            await channel.send(message)
        else:
            print("Salon Discord introuvable.")
        await bot.close()

    await bot.start(os.getenv('DISCORD_TOKEN'))

def main():
    if len(sys.argv) < 2:
        print("Erreur : Il faut passer le fichier JSON des détections en paramètre.")
        sys.exit(1)

    detection_file = sys.argv[1]
    if not os.path.exists(detection_file):
        print(f"Erreur : Le fichier {detection_file} n'existe pas.")
        sys.exit(1)

    try:
        detection_list = load_detections_from_json(detection_file)
        create_database()
        insert_data(detection_list)
    except Exception as e:
        print(f"Erreur lors du traitement du fichier JSON : {e}")
        sys.exit(1)

    # Lancer l'envoi du message Discord si des données ont été insérées
    total_animaux = sum([det["effectif"] for det in detection_list])
    total_photos = len(set(det["image"] for det in detection_list))
    current_date_and_time = dt.now()
    if total_animaux > 0:
        message = f"[{current_date_and_time}] Mise à jour de la base de données : {total_photos} photos ont été prises et {total_animaux} animaux ont été détéctés ."
        asyncio.run(send_discord_notification(message))
    else:
        print("Aucune donnée insérée, aucun message Discord envoyé.")


if __name__ == "__main__":
    main()
