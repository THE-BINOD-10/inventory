#!/bin/bash

# Author : Sudheer Kumar
# Copyright (c) Headrun Technologies

PYTHON_PATH='MIEBACH/bin/python'
PYTHON_PATH=$1'/'$PYTHON_PATH

cd $1

$PYTHON_PATH db_backup.py $1 
