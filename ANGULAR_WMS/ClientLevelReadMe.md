Client Level ReadMe:
-------------------

For UI:

All steps need to do in "/WMS_ANGULAR/ANGULAR_WMS/app/customers/" directory.

Step1:
  Create folder in customer directory with name client name.
  ex: "sagarfab"

Step2:
  Go to client directory.
  ex: cd sagarfab

Step3:
  Copy "index.html" from app directory to here.
  copy "robots.txt" file from app directory to here.

Step4:
  Copy "manifest.json" file from app directory to here and do modifications which are required.
  ex: 1. "start_url": "/sagarfab/#/",
      2. "name": "MITEE",
      3. "short_name": "MITEE"
      4. "src": "images/brand-logos/scott.jpg"

step5:
  create simlinks for following folders to here from app directory.
  fonts, images, scripts, styles, vendor, views.

  Note: Make sure simlinks should be correct.

step6:
  create folder with name "own" and also create one more folder with name "views" inside "own" folder.

step7:
  Place sigin.html inside views folder which is developed for particulare client.

=================================================================================

For Nginx:

Step1:

  Add client location in nginx like below.
  ex:
    location /sagarfab {
      expires -1;
      root /var/www/progressive_app/customers/;
    }

Step2
  Restart Service.
  ex: sudo service nginx restart
