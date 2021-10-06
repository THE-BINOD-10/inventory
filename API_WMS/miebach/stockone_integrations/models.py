# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User, Group

# Create your models here.

class IntegrationMaster(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User)
    integration_type = models.CharField(max_length=64)
    integration_data = models.TextField()
    module_type = models.CharField(max_length=64)
    stockone_reference = models.CharField(max_length=64, default=None, null=True)
    integration_error = models.TextField()
    action_type = models.CharField(
        max_length=6,
        choices=(
            ('add', 'Add'),
            ('delete', 'Delete'),
            ('upsert', 'Upsert'),
        ),
        default='upsert',
    )
    integration_reference = models.CharField(max_length=64, default=None, null=True)
    status = models.NullBooleanField(default=None, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '%s-%s-%s-%s' % (self.user,
            self.integration_type,
            self.stockone_reference,
            self.integration_reference)

    def natural_key(self):
        return {'id': self.id, 'user': self.user, 'zone': self.zone, 'level': self.level}

    class Meta:
        index_together = (('user',), ('user', 'integration_type'), ('user', 'stockone_reference', 'module_type'))
