***Setup Intructions***
-------------------

#1. Ubuntu/Mac packages required:
    JDK
        download nad install latest jdk.
    Mono
        brew install mono (mac)
        sudo apt-get install mono (linux)
    glib-2.0
        brew install glib (mac)
        sudo apt-get install glib (linux)
    pkg-config
    export PKG_CONFIG_PATH=<pkgconfig path>:$PKG_CONFIG_PATH



#2. Python packages requied (added in requirements.pip):
    pythonnet (requires mono before installing this pip package, or the build fails. )


***Run Instructions***
----------------

#1. Activate virtual enviornment
#2. CMD: 
    python TallyBridgeApp.py
