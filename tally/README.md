***Setup Intructions***
-------------------

### 1. Ubuntu/Mac packages required:**
    1. JDK1. download nad install latest jdk.
    2. Mono
        1. brew install mono (mac)
        2. sudo apt-get install mono (linux)
    3. glib-2.0
        1. brew install glib (mac)
        2. sudo apt-get install glib (linux)
    4. pkg-config
    5. export PKG_CONFIG_PATH=<pkgconfig path>:$PKG_CONFIG_PATH

### 2. Python packages requied (added in requirements.pip):
    pythonnet (requires mono before installing this pip package, or the build fails. )

***Run Instructions***
----------------
### 1. Activate virtual enviornment
    source <path to venev>
### 2. CMD: 
    python TallyBridgeApp.py
