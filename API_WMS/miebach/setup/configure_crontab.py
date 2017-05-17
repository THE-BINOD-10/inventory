from crontab import CronTab
import os

class ConfigureCrontab:
    def __init__(self):
        self.cwd = os.getcwd()
        self.project_dir = self.cwd.split('/')[-3]

    def set_crontab(self, command, schedule):

        cron = CronTab(tabfile='/etc/crontab', user=False)

        cron_obj = cron.find_command(command)
        for item in cron_obj:
            if item.command == command:
                break
        else:
            job = cron.new(command=command, user='root')
            job.setall(schedule)
            job.enable()

            cron.write()

    def cronjob_data(self):
        data = { '/usr/local/bin/lockrun --lockfile /tmp/%s_user.lock -- /bin/bash %s/populate_user_data.sh %s 1>> /tmp/%s_user_log 2>> /tmp/%s_user_err' % (self.project_dir, self.cwd, self.cwd, self.project_dir, self.project_dir): '* * * * *',
                 '/usr/local/bin/lockrun --lockfile /tmp/%s_db_backup.lock -- /bin/bash %s/db_backup.sh %s 1>> /tmp/%s_db_backup_log 2>> /tmp/%s_db_backup_err' % (self.project_dir, self.cwd, self.cwd, self.project_dir, self.project_dir): '0 * * * *' }
        for command, schedule in data.iteritems():
            self.set_crontab(command, schedule)

if __name__ == "__main__":
    OBJ = ConfigureCrontab()
    OBJ.cronjob_data()
