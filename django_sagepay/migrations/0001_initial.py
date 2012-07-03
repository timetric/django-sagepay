# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SagePayTransaction'
        db.create_table('django_sagepay_sagepaytransaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('vendor_tx_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=40)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('request', self.gf('jsonfield.fields.JSONField')()),
            ('response', self.gf('jsonfield.fields.JSONField')()),
            ('extra_data', self.gf('jsonfield.fields.JSONField')()),
            ('notification_date', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('notification_data', self.gf('jsonfield.fields.JSONField')(null=True)),
            ('acknowledgement_data', self.gf('jsonfield.fields.JSONField')(null=True)),
        ))
        db.send_create_signal('django_sagepay', ['SagePayTransaction'])


    def backwards(self, orm):
        
        # Deleting model 'SagePayTransaction'
        db.delete_table('django_sagepay_sagepaytransaction')


    models = {
        'django_sagepay.sagepaytransaction': {
            'Meta': {'object_name': 'SagePayTransaction'},
            'acknowledgement_data': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_data': ('jsonfield.fields.JSONField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notification_data': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'notification_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'request': ('jsonfield.fields.JSONField', [], {}),
            'response': ('jsonfield.fields.JSONField', [], {}),
            'vendor_tx_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'})
        }
    }

    complete_apps = ['django_sagepay']
