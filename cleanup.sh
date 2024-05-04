#!/bin/bash
ls $the_path
pkill -f "python3 -u /home/sc-sniper/main.py"
rm /home/sc-sniper/dbs/calls.db
rm /home/sc-sniper/dbs/jobs.sqlite
rm /home/sc-sniper/logs/*.log
python3 /home/sc-sniper/init_db.py