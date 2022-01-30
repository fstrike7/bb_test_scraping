#! /bin/sh
sudo rm /var/lib/mongodb/mongod.lock
sudo mongod --repair
sudo service mongod start
python3 main.py