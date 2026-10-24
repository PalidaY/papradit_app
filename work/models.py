import uuid
from django.db import models
from django.db.models import Q
class Record(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User',on_delete=models.PROTECT)
    class Meta: abstract=True
class ProductionRequest(Record):
    number = models.CharField('เลข PR',max_length=80,unique=True)
    po_number = models.CharField('เลข PO (อ้างอิง)',max_length=80,blank=True,db_index=True)
    pi_number = models.CharField('PI No.',max_length=80,blank=True)
    job = models.ForeignKey('catalog.Job',on_delete=models.PROTECT,verbose_name='งาน / ลูกค้า')
    context = models.CharField('บริบทธุรกิจ (ไม่ใช่การแยกนิติบุคคล)',max_length=10,choices=[('PPD','Papradit / PPD'),('GPT','GPT')],default='PPD')
    requester = models.CharField('ผู้ขอ',max_length=200)
    request_date = models.DateField('วันที่รับ PR')
    due_date = models.DateField('กำหนดส่ง',db_index=True)
    status = models.CharField(max_length=12,choices=[('draft','ร่าง'),('posted','เปิดงาน'),('closed','ปิดงาน'),('cancelled','ยกเลิก')],default='draft',db_index=True)
    reason = models.TextField(blank=True)
    submission_key = models.UUIDField(unique=True)
    posted_at = models.DateTimeField(null=True,blank=True)
    class Meta: ordering=['due_date','number']
    def __str__(self): return self.number
class PRLine(Record):
    request = models.ForeignKey(ProductionRequest,on_delete=models.PROTECT,related_name='lines')
    product = models.ForeignKey('catalog.Product',on_delete=models.PROTECT,verbose_name='สินค้า')
    size = models.CharField('ไซซ์',max_length=40)
    quantity = models.PositiveIntegerField('จำนวน')
    fabric_reference = models.CharField('ผ้า (ข้อมูลอ้างอิงเท่านั้น)',max_length=200,blank=True)
    color = models.CharField('สี',max_length=80,blank=True)
    source_pp_id = models.CharField('Source pp_id',max_length=100,blank=True)
    source_pr_list_id = models.CharField('Source pr_list_id',max_length=100,blank=True)
    source_ps_id = models.CharField('Source ps_id',max_length=100,blank=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name='line_quantity_positive')]
    def __str__(self): return f'{self.request} · {self.product} · {self.size}'
class LineStep(models.Model):
    line = models.ForeignKey(PRLine,on_delete=models.PROTECT,related_name='steps')
    step = models.ForeignKey('catalog.WorkStep',on_delete=models.PROTECT)
    class Meta: constraints=[models.UniqueConstraint(fields=['line','step'],name='unique_line_step')]
class Assignment(Record):
    line_step = models.ForeignKey(LineStep,on_delete=models.PROTECT,related_name='assignments')
    worker = models.ForeignKey('catalog.Worker',on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    business_date = models.DateField()
    due_date = models.DateField()
    payment_due_date = models.DateField(null=True,blank=True)
    wage_rate = models.ForeignKey('catalog.WageRate',on_delete=models.PROTECT)
    unit_wage = models.DecimalField(max_digits=14,decimal_places=4)
    currency = models.CharField(max_length=3,default='THB')
    settlement_status = models.CharField(max_length=20,default='not_configured',editable=False)
    source_assign_id = models.CharField(max_length=100,blank=True)
    submission_key = models.UUIDField(unique=True)
    reversed_at = models.DateTimeField(null=True,blank=True)
    reversal_reason = models.TextField(blank=True)
    class Meta: constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name='assignment_quantity_positive')]
class QCReceipt(Record):
    assignment = models.ForeignKey(Assignment,on_delete=models.PROTECT,related_name='receipts')
    business_date = models.DateField()
    accepted = models.PositiveIntegerField(default=0)
    rejected = models.PositiveIntegerField(default=0)
    rework = models.PositiveIntegerField(default=0)
    note = models.TextField(blank=True)
    submission_key = models.UUIDField(unique=True)
    reversed_at = models.DateTimeField(null=True,blank=True)
    reversal_reason = models.TextField(blank=True)
    class Meta: constraints=[models.CheckConstraint(condition=Q(accepted__gt=0)|Q(rejected__gt=0)|Q(rework__gt=0),name='receipt_nonempty')]
class Delivery(Record):
    line = models.ForeignKey(PRLine,on_delete=models.PROTECT,related_name='deliveries')
    quantity = models.PositiveIntegerField()
    business_date = models.DateField()
    reference = models.CharField(max_length=100)
    reversed_at = models.DateTimeField(null=True,blank=True)
    reversal_reason = models.TextField(blank=True)
    submission_key = models.UUIDField(unique=True)
    class Meta: constraints=[models.CheckConstraint(condition=Q(quantity__gt=0),name='delivery_positive')]
