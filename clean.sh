#pip install -r requirements.txt
rm database.db
python backend/init_db.py
python backend/init_group_categories.py
#python backend/server.py
