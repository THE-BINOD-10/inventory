Installing requirements:

1.Install Node.js & Npm.
  commands : curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
                   ( or )
             sudo apt-get install nodejs

2.Install bower and grunt-cli.
  command : npm install --global bower grunt-cli

3.Run npm install.
  command : npm install

4.Run bower install.
  commang : bower install

5.After installing bower it will install all dependencies in "bower_components" directory.Move bower_components folder into app directory with the name "vendor".

6.Change api url in following directory.
  directory : 'app/scripts/extentions/auth/session.js'

7.Please check firebase url in "index.html" before starting the project. If it contains prod firebase then change it to some other.

8.Finally To run project use following command.Run this command where 'Gruntfile.js' exist.
  command : grunt serve
  NOTE    : you can change UI Port number in Gruntfile.js
