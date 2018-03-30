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
  command : bower install

5.After installing bower it will install all dependencies in "bower_components" directory.Move bower_components folder into app directory with the name "vendor".

6.to install sweetalert please run below command
  command : npm install sweetalert@1.1.0
  after that move sweetalert directory from nodemodules directory to vendor directory.

7.Please point index file based on the environment in nginx configuration file.

    Development -->  dev.html
    Staging     -->  staging.html
    Production  -->  prod.html

8.Check api url in following directory.
   Dev:  directory : 'app/scripts/extentions/auth/dev_session.js'
   Staging: directory : 'app/scripts/extentions/auth/staging_session.js'
   Prod:  directory : 'app/scripts/extentions/auth/prod_session.js'

9.Finally To run project use following command.Run this command where 'Gruntfile.js' exist.
  command : grunt serve
  NOTE    : you can change UI Port number in Gruntfile.js
