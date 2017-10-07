# WMS
Warehouse Management Systems

Installing requirements:

1.Installing Pip and Creating Virtual Environment.
  Goto this path API_WMS/miebach/setup and Run the following command
  commands : sh setup.sh

2.Installing Django and other related packages.
  Activate virtualenv
  commands : source MIEBACH/bin/activate
             pip install -r requirements.pip

3.If there is any problem to install Mysql-python.Execute the following command
   command: sudo apt-get install build-essential libssl-dev libffi-dev python-dev

4.For New Database.
  commands : python manage.py makemigrations miebach_admin
             python manage.py migrate
             python manage.py migrate oauth2_provider

5.Check the Database settings and change if it is not Production setup.
