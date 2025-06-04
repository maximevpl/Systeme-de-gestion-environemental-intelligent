# Biolens
#### Un projet d'étude pratique de 3INFO (by Amaury, Iwen, Marc, Mathys, Maxime)

[![Build Status](https://travis-ci.org/joemccann/dillinger.svg?branch=master)](https://travis-ci.org/joemccann/dillinger)

> L'objectif de l’étude pratique est de développer une application d'analyse vidéo basée sur l'IA et de l'intégrer au système Mycélium. L'application traitera un flux vidéo, analysera le contenu à l'aide d'algorithmes d'IA, stockera des données historiques et enverra des alertes en fonction des éléments détectés. L'application sera structurée comme un ensemble de fonctions FaaS reparties entre les objets connectés, le fog et le cloud. L'application se basera sur un prototype initial, conçu par un groupe d'étudiants de l'INSA, qui recense les animaux du campus. Ce prototype est composé d'un Raspberry Pi équipé d'une caméra et d'un serveur exécutant un modèle de classification d'images pré-entraîné.

## Ressources utiles
- [Tuto faasd sur Raspberry]
- [Video de déploiement d'une fonction sur faasd]
- [Doc d'Openfaas]

## Guide d'installation

#### Part 1

Installer une distribution 64 bits sur le raspberry (Raspberry pi OS lite 64 bits par exemple)
--> Utiliser raspberry imager et flasher une carte SD

#### Part 2

*Pour l'installation, je me suis mis en administrateur avec `sudo -i`* 

Installer faasd sur le raspberry : 
```sh
git clone https://github.com/openfaas/faasd
cd faasd
./hack/install.sh
```
Il est possible qu'il y ait un problème de version empêchant le gateway de fonctionner. Vérfier dans le fichier situé à `/var/lib/faasd/`
tel que 
```sh
sudo nano /var/lib/faasd/docker-compose.yml
```
renvoie un fichier avec 
```sh
gateway:
    image: ghcr.io/openfaas/gateway:0.27.12
```
si la version de l'image n'est pas 12 (ou la dernière [ici](https://github.com/openfaas/faas/pkgs/container/gateway)), remplacer la version à la main, enregistrez le fichier puis appliquer le changement en faisant `systemctl daemon-reload`
Enfin, vérifiez l'état avec : 
```sh
sudo systemctl status faasd
sudo systemctl status faasd-provider
```
et les logs :
```sh
sudo journalctl -u faasd --lines 40
sudo journalctl -u faasd-provider --lines 40
```

#### Part 3

A ce stade, vous devriez pouvoir accéder à l'interface Openfaas dans le navigateur. Pour ce faire, accéder à l'adresse `http://<ip_du_raspberry>:8080`
Un pop-up de connexion devrait apparaitre : pour vous connecter, le login est *admin* et le mot de passe est accessible en exécutant sur le raspberry `sudo cat /var/lib/faasd/secrets/basic-auth-password`

Sur le raspberry, connectez vous au client openfaas (faas-cli) en faisant : 
```sh
sudo cat /var/lib/faasd/secrets/basic-auth-password | faas-cli login --password-stdin
```

#### Part 4
> Du fait de l'utilisation de faasd, l'installation de Docker sur le raspberry n'est pas recommandée du tout (possibilité de conflit avec containerd, intégré à faasd). Pour autant, il est nécessaire d'utiliser Docker pour construire une architecture de fonction à partir des templates disponibles. Pour ce faire, nous allons donc devoir utiliser un PC, sur lequel nous créerons la fonction, que nous déploierons par la suite sur le raspberry avec faasd. Cette partie couvre toutes les étapes pour déployer finalement une fonction sur le raspberry

La suite de l'installation va donc se faire sur votre PC : 

Installer Docker s'il n'est pas déjà installé :
https://docs.docker.com/engine/install/

Créer un compte docker sur https://hub.docker.com puis connectez vous sur votre PC avec
```sh
docker login
```

Installer faas-cli dessus en faisant 
````sh
curl -sLfS https://cli.openfaas.com | sudo sh
````
Pour voir les langages de programmations disponibles, faites 
```sh
faas-cli template store list
```
Une fois le langage choisit, récupérez le avec
````sh
faas-cli template store pull <votre-langage>
Exemple : faas-cli template store pull python3-http-debian
````
Vérifiez l'exécution en faisant `faas-cli new --list`, votre langage devrait apparaitre comme disponible

Pour créer une fonction, placez vous dans le dossier souhaité pour la fonction, puis faites 
```sh
faas-cli new --lang <votre-langage> <nom-de-la-fonction> --prefix <username-de-docker>
Exemple : faas-cli new --lang python3-http-debian hello-python --prefix etudepratique
````
Vous devrez après cela trouver votre fonction au sein du dossier du nom de la fonction passé dans la commande précédente.
Il ne reste maintenant plus qu'à déployer la fonction sur le raspberry. Pour ce faire, connectez vous à faas-cli sur votre PC avec :
````sh
export OPENFAAS_URL=http://<ip-du-raspberry>:8080
scp <user>@<ip-du-raspberry>:/var/lib/faasd/secrets/basic-auth-password | faas-cli login --password-stdin
````
Vérifiez la connexion en faisant `faas-cli version`qui devrait renvoyer une réponse avec la présence d'une partie *gateway* et d'une partie *provider*`

Enfin, placez vous dans le dossier contenant le fichier <nom-de-fonction>.yml, puis faites :
```sh
faas-cli publish -f <nom-de-fonction>.yml --platforms linux/arm64,linux/amd64
```
Enfin déployer la fonction avec 
```sh
faas-cli deploy -f <nom-de-fonction>.yml
```

Vous devriez maintenant voir apparaitre votre fonction sur l'interface web de openfaas accessible à http://<ip_du_raspberry>:8080. Pour invoquer votre fonction, faites une simple requête http vers l'adresse http://<ip_du_raspberry>:8080/function/<nom-de-fonction>


*Globalement, cette partie reprend ce [Tuto de Alex Ellis][Tuto faasd sur Raspberry] à partir de 34:00*

#### Part 5

Petit point sur les différents chemins utilisés : 

##### Sur le Raspberry :

- `~/biolens/pictures/` : dossier contenant le fichier JSON des détections en cours, et un dossier images contenant les images des détections en cours
- `~/biolens/detections/`: dossier contenant le script python permettant les détections de mouvement
Pour lancer ce script, il faut d'abord démarrer l'environnement virtuel en se placant dans le dossier detections et en faisant : 
```sh
source motion_env/bin/activate
```
puis faites 
```sh
python3 motion.py
```
- `~/biolens/yolo/`: dossier contenant le script yolo permettant la reconnaissance d'animaux dans les images
Pour lancer ce script, il faut d'abord démarrer l'environnement virtuel en se placant dans le dossier biolens et en faisant : 
```sh
source ultralytics-env/bin/activate
```
puis faites 
```sh
cd yolo
```
```sh
python3 traitement_image.py
```
- `~/biolens/storage/`: dossier contenant temporairement le fichier JSON des détections traitées par la fonction de tri et le dossier image des images prêtes à être envoyé. Ce dossier contient temporairement des données, qui sont soit envoyé par la fonction envoie soit remise dans le dossier pictures si l'envoie échoue
- `~/biolens/logs/`: dossier contenant le fichier JSON des logs de la fonction envoie.

##### Sur le cloud :

- `~/biolens/yolo/`: dossier contenant le script yolo permettant la reconnaissance d'animaux dans les images
Pour lancer ce script, il faut d'abord démarrer l'environnement virtuel en se placant dans le dossier yolo et en faisant :  
```sh
source env/bin/activate
```
puis faites
```sh
python3 traitement_cloud.py
```
- `~/biolens/data/` : dossier contenant le fichier JSON des détections, et un dossier images contenant les images des détections
- `~/biolens/bdd/` : dossier contenant le fichier detections.db de la base de donnée, et un dossier images contenant les images des entrées de la base de données

### Part 6

Quelques commandes utiles pour gérer les connexions ssh avec le raspberry et permettre aux fonctions de communiquer via ssh

Créer une clé ssh (sans mot de passe pour simplifier la connexion des fonctions avec le raspberry) :
```sh
ssh-keygen -t rsa -b 4096 -f ~/.ssh/faas_key -N ""
```

Envoyer la clé sur le raspberry : 
```sh
ssh-copy-id -i ~/.ssh/faas_key.pub fox@<ip_du_raspberry>
```

Ajouter la clé à openfaas pour les fonctions :
```sh
faas-cli secret create ssh-private-key --from-file ~/.ssh/faas_key
```



## Tech

Biolens uses a number of open source projects to work properly:

- [Faasd] - Version légère de OpenFaaS fonctionnant sans orchestrateur complexe comme Kubernetes.
- [Docker] - Plateforme permettant de créer, déployer et exécuter des conteneurs.
- [Python] - Langage de programmation polyvalent, apprécié pour sa simplicité et sa large communauté.
- [Faas-cli] - Interface en ligne de commande pour gérer les fonctions OpenFaaS.

## Tips
- ##### Installer un paquet python avec pip (Exemple ici avec ultralytics) :

```sh
python3 -m venv ultralytics-env
source ultralytics-env/bin/activate
pip install ultralytics
```
Pour sortir de l'environnement : `deactivate`

- ##### Envoyer/Recevoir un fichier :

Envoyer : 
```
scp chemin/vers/fichier <user>@<ip-du-raspberry>:/chemin/cible/
```
Recevoir : 
```
scp <user>@<ip-du-raspberry>:/chemin/du/fichier .
```
## Usefull Links
Vous trouverez ici des sources ayant été utile au cours du projet, sans pour autant qu'elles s'intègrent dans une étape précise du développement

| Sujet | lien |
| ------ | ------ |
| Doc caméra Raspberry | https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf |
| Setup NATS | https://willschenk.com/labnotes/2021/setting_up_services_with_faasd/ |

## Login utiles
- [Raspberry] - login : fox ; passwd : foxinsarennes/foxinsa

## License

INSA Rennes, 3INFO, by Amaury, Iwen, Marc, Mathys, Maxime

**Free Software, Hell Yeah!**