Installing requirements:

1.Install Node.js & Npm.
  commands : curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
             sudo apt-get install nodejs

2.Install bower and grunt-cli.
  command : npm install --global bower grunt-cli

3.Run npm install.

4.Run bower install.

5.Change api url in following directory.
  directory : 'app/scripts/extensions/auth/session.js'

5.Finally To run project use following command.Run this command where 'Gruntfile.js' exist.
  command : grunt serve
