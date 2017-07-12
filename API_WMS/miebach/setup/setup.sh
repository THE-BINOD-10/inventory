#!/bin/bash

# Author : Sudheer Kumar
# Copyright (c) Headrun Technologies

#Installing required dependancies
# source ElasticSearch.sh 1.5.0
# source Kibana 4.1.1
# source Logstash.sh 1.5.3
sudo python get-pip.py
sudo apt-get install python-virtualenv
virtualenv MIEBACH
#source MIEBACH/bin/activate
#pip install -r requirements.pip

# Configuring crontab for users dump
# gcc lockrun.c -o lockrun
# cp -u lockrun /usr/local/bin/
# sudo python configure_crontab.py
