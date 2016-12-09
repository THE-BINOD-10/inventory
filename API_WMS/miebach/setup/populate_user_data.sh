#!/bin/bash

# Author : Sudheer Kumar
# Copyright (c) Headrun Technologies

STEP_BACK='/../'
PYTHON_PATH='MIEBACH/bin/python'
PROJECT_PATH=$1$STEP_BACK
PYTHON_PATH=$1'/'$PYTHON_PATH

cd $PROJECT_PATH

$PYTHON_PATH collect_user_data.py
