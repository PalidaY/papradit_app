from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from catalog.models import WageRate, WorkStep
from core.models import SourceIdentity
from core.permissions import audit
from .models import ProductionRequest, PRLine, LineStep, Assignment, QCReceipt, Delivery

def totals(assignment):
    values=assignment.receipts.filter(reversed_at__isnull=True).aggregate(a=Sum('accepted'),r=Sum('rejected'),w=Sum('rework'))
    accepted,rejected,rework=[values[k] or 0 for k in ['a','r','w']]
    return {'accepted':accepted,'rejected':rejected,'rework':rework,'received_attempts':accepted+rejected+rework,'with_worker':assignment.quantity-accepted-rejected}
def progress(line_step):
    assignments=line_step.assignments.filter(reversed_at__isnull=True)
    result={'assigned':0,'accepted':0,'rejected':0,'rework':0,'received_attempts':0,'with_worker':0}
    for assignment in assignments:
        result['assigned']+=assignment.quantity
        for k,v in totals(assignment).items(): result[k]+=v
    result['available']=line_step.line.quantity-result['assigned']+result['rejected']
    return result
def delivered(line): return line.deliveries.filter(reversed_at__isnull=True).aggregate(q=Sum('quantity'))['q'] or 0
def deliverable(line):
    counts=[progress(s)['accepted'] for s in line.steps.all()]
    return min(counts) if counts else 0

def replay(model,key,actor,**expected):
    item=model.objects.filter(submission_key=key).first()
    if item:
        if item.created_by_id!=actor.pk or any(getattr(item,k)!=v for k,v in expected.items()):
            raise ValidationError('Submission key was already used for a different transaction.')
    return item

@transaction.atomic
def create_pr(actor,header,lines,key):
    existing=replay(ProductionRequest,key,actor,**header)
    if existing: return existing
    if not lines: raise ValidationError('เพิ่มสินค้าอย่างน้อยหนึ่งรายการ')
    if header['due_date']<header['request_date']: raise ValidationError('กำหนดส่งต้องไม่ก่อนวันที่รับ PR')
    pr=ProductionRequest.objects.create(created_by=actor,submission_key=key,**header)
    for data in lines:
        line=PRLine(request=pr,created_by=actor,**data); line.full_clean(); line.save()
        for entity,source_id in [('pp_id',line.source_pp_id),('pr_list_id',line.source_pr_list_id),('ps_id',line.source_ps_id)]:
            if source_id:
                SourceIdentity.objects.create(source='manual-source-mapping',entity=entity,source_id=source_id,target_kind='pr_line',target_id=line.pk)
    audit(actor,'work.create',pr.pk,after={'number':pr.number,'lines':len(lines)})
    return pr

@transaction.atomic
def post_pr(actor,pr_id):
    pr=ProductionRequest.objects.select_for_update().get(pk=pr_id)
    if pr.status=='posted': return pr
    if pr.status!='draft': raise ValidationError('เฉพาะร่างเท่านั้นที่เปิดงานได้')
    steps=list(WorkStep.objects.filter(job=pr.job,active=True))
    if not steps: raise ValidationError('เพิ่มขั้นตอนใน Catalog งานก่อนเปิด PR')
    if not pr.lines.exists(): raise ValidationError('PR ต้องมีรายการสินค้า')
    for line in pr.lines.all():
        for step in steps: LineStep.objects.get_or_create(line=line,step=step)
    pr.status='posted'; pr.posted_at=timezone.now(); pr.save(update_fields=['status','posted_at'])
    audit(actor,'work.post',pr.pk,after={'steps_per_line':len(steps)})
    return pr

@transaction.atomic
def assign(actor,line_step,worker,quantity,business_date,due_date,price_type,key,payment_due_date=None):
    pr=ProductionRequest.objects.select_for_update().get(pk=line_step.line.request_id)
    line=PRLine.objects.select_for_update().get(pk=line_step.line_id)
    existing=replay(Assignment,key,actor,line_step_id=line_step.pk,worker_id=worker.pk,quantity=quantity,business_date=business_date,due_date=due_date,payment_due_date=payment_due_date)
    if existing:
        if existing.wage_rate.price_type!=price_type: raise ValidationError('Submission key reused with another price type.')
        return existing
    if pr.status!='posted': raise ValidationError('PR ยังไม่เปิดงาน')
    if not worker.active: raise ValidationError('ผู้รับจ้างถูกปิดใช้งาน')
    if quantity<=0 or quantity>progress(line_step)['available']: raise ValidationError('จำนวนจ่ายงานเกินจำนวนที่ยังจ่ายได้')
    if due_date<business_date: raise ValidationError('กำหนดส่งต้องไม่ก่อนวันจ่ายงาน')
    WorkStep.objects.select_for_update().get(pk=line_step.step_id)
    rates=WageRate.objects.filter(step=line_step.step,price_type=price_type,effective_from__lte=business_date).filter(Q(effective_to__isnull=True)|Q(effective_to__gt=business_date))
    if rates.count()!=1: raise ValidationError('ไม่พบอัตราค่าแรงเดียวที่ตรงกับวันที่และประเภท กรุณาให้ผู้ดูแลราคาแก้ไข')
    rate=rates.get()
    a=Assignment.objects.create(created_by=actor,line_step=line_step,worker=worker,quantity=quantity,business_date=business_date,due_date=due_date,payment_due_date=payment_due_date,wage_rate=rate,unit_wage=rate.amount,submission_key=key)
    audit(actor,'work.assign',a.pk,after={'quantity':quantity,'wage_rate_id':str(rate.pk)})
    return a

@transaction.atomic
def receive(actor,assignment,business_date,accepted,rejected,rework,note,key):
    ProductionRequest.objects.select_for_update().get(pk=assignment.line_step.line.request_id)
    PRLine.objects.select_for_update().get(pk=assignment.line_step.line_id)
    assignment=Assignment.objects.select_for_update().get(pk=assignment.pk)
    existing=replay(QCReceipt,key,actor,assignment_id=assignment.pk,business_date=business_date,accepted=accepted,rejected=rejected,rework=rework,note=note)
    if existing: return existing
    if assignment.reversed_at or assignment.line_step.line.request.status!='posted': raise ValidationError('รายการนี้ไม่เปิดรับงาน')
    if business_date<assignment.business_date: raise ValidationError('วันรับงานต้องไม่ก่อนวันจ่ายงาน')
    if min(accepted,rejected,rework)<0 or accepted+rejected+rework<=0 or accepted+rejected+rework>totals(assignment)['with_worker']: raise ValidationError('จำนวนรับ/QC เกินจำนวนที่อยู่กับช่าง หรือไม่มีจำนวนรับ')
    if (rejected or rework) and not note.strip(): raise ValidationError('ระบุเหตุผลสำหรับงานไม่ผ่าน / ส่งแก้')
    receipt=QCReceipt.objects.create(created_by=actor,assignment=assignment,business_date=business_date,accepted=accepted,rejected=rejected,rework=rework,note=note,submission_key=key)
    audit(actor,'work.qc',receipt.pk,after={'accepted':accepted,'rejected':rejected,'rework':rework})
    return receipt

@transaction.atomic
def deliver(actor,line,quantity,business_date,reference,key):
    pr=ProductionRequest.objects.select_for_update().get(pk=line.request_id)
    line=PRLine.objects.select_for_update().get(pk=line.pk)
    existing=replay(Delivery,key,actor,line_id=line.pk,quantity=quantity,business_date=business_date,reference=reference)
    if existing: return existing
    if pr.status!='posted' or quantity<=0 or quantity>deliverable(line)-delivered(line): raise ValidationError('ส่งมอบได้ไม่เกินจำนวนผ่าน QC ครบทุกขั้นตอนและยังไม่ส่งมอบ')
    if business_date<pr.request_date: raise ValidationError('วันที่ส่งมอบก่อนวันรับ PR')
    d=Delivery.objects.create(created_by=actor,line=line,quantity=quantity,business_date=business_date,reference=reference,submission_key=key)
    audit(actor,'work.deliver',d.pk,after={'quantity':quantity})
    return d

@transaction.atomic
def reverse(actor,kind,pk,reason):
    if not reason.strip(): raise ValidationError('กรุณาระบุเหตุผลการกลับรายการ')
    model={'assignment':Assignment,'receipt':QCReceipt,'delivery':Delivery}[kind]
    obj=model.objects.get(pk=pk)
    a=None if kind=='delivery' else (obj if kind=='assignment' else obj.assignment)
    line_id=obj.line_id if kind=='delivery' else a.line_step.line_id
    original_line=PRLine.objects.get(pk=line_id)
    pr=ProductionRequest.objects.select_for_update().get(pk=original_line.request_id)
    line=PRLine.objects.select_for_update().get(pk=line_id)
    obj=model.objects.select_for_update().get(pk=pk)
    if obj.reversed_at: return obj
    if pr.status!='posted': raise ValidationError('เปิด PR อีกครั้งก่อนกลับรายการ')
    if kind=='assignment' and obj.receipts.filter(reversed_at__isnull=True).exists(): raise ValidationError('กลับรายการ QC ก่อนกลับรายการจ่ายงาน')
    obj.reversed_at=timezone.now(); obj.reversal_reason=reason; obj.save(update_fields=['reversed_at','reversal_reason'])
    if (a is not None and progress(a.line_step)['available']<0) or delivered(line)>deliverable(line): raise ValidationError('การกลับรายการจะขัดกับจำนวนจ่ายงานหรือส่งมอบที่ลงไว้แล้ว')
    audit(actor,'work.reverse',obj.pk,after={'kind':kind,'reason':reason})
    return obj

@transaction.atomic
def close_pr(actor,pk,status,reason):
    pr=ProductionRequest.objects.select_for_update().get(pk=pk)
    if pr.status!='posted' or status not in ['closed','cancelled'] or not reason.strip(): raise ValidationError('สถานะไม่ถูกต้อง หรือยังไม่ได้ระบุเหตุผล')
    for line in pr.lines.all():
        if any(progress(s)['with_worker'] for s in line.steps.all()): raise ValidationError('ยังมีงานอยู่กับช่าง')
        if status=='closed' and delivered(line)!=line.quantity: raise ValidationError('ยังส่งมอบไม่ครบ')
        if status=='cancelled' and (line.deliveries.filter(reversed_at__isnull=True).exists() or any(progress(s)['accepted'] for s in line.steps.all())): raise ValidationError('มีงานผ่าน QC/ส่งมอบแล้ว ไม่สามารถยกเลิกได้')
    pr.status=status; pr.reason=reason; pr.save(update_fields=['status','reason'])
    audit(actor,'work.'+status,pr.pk,after={'reason':reason})

@transaction.atomic
def update_pr(actor,pk,header,lines):
    pr=ProductionRequest.objects.select_for_update().get(pk=pk)
    if pr.status!='draft': raise ValidationError('แก้ไขได้เฉพาะร่าง')
    if header['due_date']<header['request_date']: raise ValidationError('กำหนดส่งต้องไม่ก่อนวันที่รับ PR')
    before={'number':pr.number,'line_count':pr.lines.count()}
    for k,v in header.items(): setattr(pr,k,v)
    pr.full_clean(); pr.save()
    for data in lines:
        data=dict(data); existing=data.pop('id',None)
        if existing:
            line=pr.lines.get(pk=existing.pk)
            for k,v in data.items(): setattr(line,k,v)
            line.full_clean(); line.save()
        else:
            line=PRLine(request=pr,created_by=actor,**data); line.full_clean(); line.save()
            for entity,sid in [('pp_id',line.source_pp_id),('pr_list_id',line.source_pr_list_id),('ps_id',line.source_ps_id)]:
                if sid: SourceIdentity.objects.create(source='manual-source-mapping',entity=entity,source_id=sid,target_kind='pr_line',target_id=line.pk)
    audit(actor,'work.update_draft',pk,before=before,after={'number':pr.number,'line_count':pr.lines.count()})
    return pr
