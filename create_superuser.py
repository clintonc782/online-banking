# create_superuser.py
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "onlineBanking.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Change these to your preferred credentials
USERNAME = "Chinnyt"
EMAIL = "skybank.com"
PASSWORD = "Chinny200"

if not User.objects.filter(username=USERNAME).exists():
    User.objects.create_superuser(username=USERNAME, email=EMAIL, password=PASSWORD)
    print("Superuser created!")
else:
    print("Superuser already exists.")