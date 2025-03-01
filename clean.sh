#pip install -r requirements.txt
mv /var/www/database.db /var/www/database-copy-$(date +"%Y%m%d-%H%M%S").db
python backend/init_db.py
python backend/init_group_categories.py
#python backend/server.py
www
