import uuid
from django.db import models
from django.db.models import Q
class Master(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    code = models.CharField('รหัส',max_length=80,unique=True)
    name = models.CharField('ชื่อ',max_length=200)
    active = models.BooleanField('เปิดใช้งาน',default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract=True; ordering=['code']
    def __str__(self): return f'{self.code} · {self.name}'
class Product(Master):
    category = models.CharField('หมวดหมู่',max_length=100,blank=True)
class Job(Master):
    description = models.TextField('รายละเอียด / ข้อกำหนดลูกค้า',blank=True)
class Pattern(Master): pass
class Worker(Master):
    kind = models.CharField('ประเภท',max_length=20,choices=[('worker','ช่าง'),('supplier','ผู้รับจ้าง')],default='worker')
    contact = models.CharField('ข้อมูลติดต่อ',max_length=200,blank=True)
class WorkStep(Master):
    job = models.ForeignKey(Job,on_delete=models.PROTECT,verbose_name='งาน')
    pattern = models.ForeignKey(Pattern,on_delete=models.PROTECT,null=True,blank=True,verbose_name='รูปแบบ')
    sequence = models.PositiveIntegerField('ลำดับ',default=1)
    class Meta: ordering=['sequence','code']
class WageRate(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    step = models.ForeignKey(WorkStep,on_delete=models.PROTECT,verbose_name='ขั้นตอนงาน')
    amount = models.DecimalField('ค่าแรงต่อชิ้น (THB)',max_digits=14,decimal_places=4)
    effective_from = models.DateField('มีผลตั้งแต่')
    effective_to = models.DateField('สิ้นสุด (ไม่รวมวันนี้)',null=True,blank=True)
    price_type = models.CharField('ประเภทค่าแรง',max_length=40,default='standard')
    currency = models.CharField(max_length=3,default='THB',editable=False)
    created_by = models.ForeignKey('auth.User',on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-effective_from']
        constraints=[models.CheckConstraint(condition=Q(amount__gte=0),name='wage_nonnegative'),models.CheckConstraint(condition=Q(effective_to__isnull=True)|Q(effective_to__gt=models.F('effective_from')),name='wage_date_order')]
    def __str__(self): return f'{self.step} / {self.price_type} / {self.effective_from}'
