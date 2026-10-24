from django.conf import settings
from django.db import models
from django.db.models import Q
MODULES = [('admin','ผู้ใช้และสิทธิ์'),('catalog.products','Catalog สินค้า'),('catalog.jobs','Catalog งาน'),('catalog.wages','Catalog ค่าแรง'),('catalog.fabrics','Catalog ผ้า'),('catalog.materials','Catalog วัตถุดิบ'),('work','รับจ่ายงาน'),('fabric','เบิกคืนผ้า + ห้องตัด'),('materials','เบิกคืนวัตถุดิบ'),('fixed_costs','ต้นทุน Fix cost')]
ACTIONS = [(x,x) for x in ['read','create','update_draft','post','reverse','export','read_financial','manage_prices','lookup_catalog','manage_users','manage_permissions']]
class ModuleGrant(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,null=True,blank=True)
    group = models.ForeignKey('auth.Group',on_delete=models.CASCADE,null=True,blank=True)
    module = models.CharField(max_length=40,choices=MODULES)
    action = models.CharField(max_length=30,choices=ACTIONS)
    class Meta:
        constraints = [models.CheckConstraint(condition=(Q(user__isnull=False,group__isnull=True)|Q(user__isnull=True,group__isnull=False)),name='grant_one_subject'), models.UniqueConstraint(fields=['user','module','action'],name='unique_user_grant'),models.UniqueConstraint(fields=['group','module','action'],name='unique_group_grant')]
class AccountState(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    session_version = models.PositiveIntegerField(default=0)
class LoginThrottle(models.Model):
    key = models.CharField(max_length=64,primary_key=True)
    failures = models.PositiveIntegerField(default=0)
    window_start = models.DateTimeField()
class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,null=True)
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=200)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at','-pk']
class SourceIdentity(models.Model):
    source = models.CharField(max_length=100)
    entity = models.CharField(max_length=60)
    source_id = models.CharField(max_length=200)
    target_kind = models.CharField(max_length=60)
    target_id = models.UUIDField()
    raw = models.JSONField(default=dict)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['source','entity','source_id'],name='unique_source_identity')]
