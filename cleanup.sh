#!/bin/bash
ls $the_path
rm /home/sc-sniper/dbs/calls.db
rm /home/sc-sniper/logs/*.log
python3 /home/sc-sniper/init_db.py
chmod u+rw /home/sc-sniper/dbs/calls.db
chmod u+rw /home/sc-sniper/dbs/jobs.sqlite
