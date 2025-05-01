# installation
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

pip install -r requirements.txt

# setup
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# start task manager
celery -A core worker -l info -B

