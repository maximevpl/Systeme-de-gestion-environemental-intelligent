import sqlite3
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk  # Pour afficher l'image
import os

# Connexion à la base de données
def connect_db():
    return sqlite3.connect("detections.db")


# Récupérer les animaux distincts de la base de données
def get_animals_from_db():
    """Récupère la liste des animaux distincts depuis la base de données."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Classe_animal FROM animalDetecte ORDER BY Classe_animal")
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results


# Exécuter une requête et afficher les résultats
def execute_query():
    conn = connect_db()
    cursor = conn.cursor()

    date = date_entry.get()
    classe_animal = classe_var.get()

    query = """
    SELECT p.Date, p.Heure, ad.Classe_animal, ad.Nombre, p.Chemin_image
    FROM animalDetecte ad
    JOIN photo p ON ad.IDphoto = p.IDphoto
    WHERE 1=1
    """

    params = []
    if date:
        query += " AND p.Date = ?"
        params.append(date)
    if classe_animal:
        query += " AND ad.Classe_animal = ?"
        params.append(classe_animal)

    query += " ORDER BY p.Date, p.Heure"
    cursor.execute(query, params)

    results = cursor.fetchall()
    conn.close()

    for row in tree.get_children():
        tree.delete(row)

    for row in results:
        tree.insert("", "end", values=row[:-1], tags=(row[-1],))  # On stocke le chemin en tag pour le retrouver


# Affichage de l'image sélectionnée
def on_row_double_click(event):
    selected_item = tree.selection()
    if not selected_item:
        return

    image_path = tree.item(selected_item, "tags")[0]
    if not os.path.exists(image_path):
        print("Image non trouvée :", image_path)
        return

    try:
        img_window = tk.Toplevel(root)
        img_window.title("Image associée")
        img = Image.open(image_path)
        img.thumbnail((600, 600))
        photo = ImageTk.PhotoImage(img)
        label = tk.Label(img_window, image=photo)
        label.image = photo  # Référence pour empêcher le garbage collection
        label.pack()
    except Exception as e:
        print("Erreur lors de l'affichage de l'image :", e)


# Interface Tkinter
root = tk.Tk()
root.title("Analyse des Données Animalières")
root.geometry("700x500")

frame = tk.Frame(root)
frame.pack(pady=10)

tk.Label(frame, text="Date (AAAA-MM-JJ):").grid(row=0, column=0)
date_entry = tk.Entry(frame)
date_entry.grid(row=0, column=1)

# Récupérer la liste des animaux à partir de la base de données
animal_list = get_animals_from_db()

tk.Label(frame, text="Animal:").grid(row=1, column=0)
classe_var = tk.StringVar()
classe_menu = ttk.Combobox(frame, textvariable=classe_var, values=animal_list)
classe_menu.grid(row=1, column=1)

tk.Button(frame, text="Rechercher", command=execute_query).grid(row=3, column=0, columnspan=2, pady=10)

columns = ("Date", "Heure", "Classe", "Nombre")
tree = ttk.Treeview(root, columns=columns, show="headings")
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=100)
tree.pack(pady=20)

# Ajouter l’événement double-clic
tree.bind("<Double-1>", on_row_double_click)

root.mainloop()
