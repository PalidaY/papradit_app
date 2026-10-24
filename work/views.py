import csv
from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse,HttpResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from core.permissions import require,allowed
from .models import ProductionRequest,PRLine,LineStep,Assignment,QCReceipt,Delivery
from .forms import HeaderForm,LineFormSet,AssignmentForm,ReceiptForm,DeliveryForm,ReasonForm
from . import services

def filtered(request):
    rows=ProductionRequest.objects.select_related('job').all()
    q=request.GET.get('q','').strip()
    if q: rows=rows.filter(Q(number__icontains=q)|Q(po_number__icontains=q)|Q(job__name__icontains=q)|Q(requester__icontains=q)|Q(lines__product__name__icontains=q)|Q(lines__size__icontains=q)).distinct()
    status=request.GET.get('status','')
    if status: rows=rows.filter(status=status)
    for key,lookup in [('from','due_date__gte'),('to','due_date__lte')]:
        if request.GET.get(key):
            from datetime import date
            try: value=date.fromisoformat(request.GET[key])
            except ValueError: raise ValidationError('วันที่ไม่ถูกต้อง')
            rows=rows.filter(**{lookup:value})
    if request.GET.get('overdue')=='1': rows=rows.filter(status='posted',due_date__lt=timezone.localdate())
    return rows

def line_data(line,financial=False):
    steps=[]
    for ls in line.steps.select_related('step').all():
        assignments=[]
        for a in ls.assignments.select_related('worker').order_by('created_at'):
            data={'id':str(a.pk),'worker':str(a.worker),'quantity':a.quantity,'due_date':a.due_date,'reversed':bool(a.reversed_at),'totals':services.totals(a),'receipts':list(a.receipts.order_by('created_at'))}
            if financial:
                data.update(unit_wage=a.unit_wage,accepted_value=a.unit_wage*data['totals']['accepted'],settlement_status=a.settlement_status)
            assignments.append(data)
        steps.append({'id':ls.pk,'name':str(ls.step),'progress':services.progress(ls),'assignments':assignments})
    done=services.delivered(line)
    return {'id':str(line.pk),'product':str(line.product),'size':line.size,'quantity':line.quantity,'delivered':done,'remaining':line.quantity-done,'deliverable':services.deliverable(line)-done,'steps':steps,'fabric':line.fabric_reference,'color':line.color,'source_pp_id':line.source_pp_id,'source_pr_list_id':line.source_pr_list_id,'deliveries':list(line.deliveries.order_by('created_at'))}

@require('work')
def dashboard(request):
    rows=ProductionRequest.objects.all()
    return render(request,'work/dashboard.html',{'total':rows.count(),'open_count':rows.filter(status='posted').count(),'overdue':rows.filter(status='posted',due_date__lt=timezone.localdate()).count(),'drafts':rows.filter(status='draft').count(),'recent':rows.select_related('job')[:6],'can_create':allowed(request.user,'work','create'),'can_export':allowed(request.user,'work','export')})
@require('work')
def listing(request):
    try: rows=filtered(request)
    except ValidationError as e: messages.error(request,e.messages[0]); rows=ProductionRequest.objects.none()
    from django.core.paginator import Paginator
    page=Paginator(rows,25).get_page(request.GET.get('page'))
    return render(request,'work/list.html',{'page':page,'q':request.GET.get('q',''),'can_create':allowed(request.user,'work','create'),'can_export':allowed(request.user,'work','export')})
@require('work')
def detail(request,pk):
    pr=get_object_or_404(ProductionRequest.objects.select_related('job'),pk=pk)
    financial=allowed(request.user,'work','read_financial')
    return render(request,'work/detail.html',{'pr':pr,'lines':[line_data(l,financial) for l in pr.lines.select_related('product')],'can_post':allowed(request.user,'work','post'),'can_edit':allowed(request.user,'work','update_draft'),'can_reverse':allowed(request.user,'work','reverse'),'can_financial':financial})
@require('work','create')
def create(request):
    if not allowed(request.user,'work','lookup_catalog'): raise PermissionDenied
    form=HeaderForm(request.POST or None)
    formset=LineFormSet(request.POST or None)
    if request.method=='POST' and form.is_valid() and formset.is_valid():
        header={k:v for k,v in form.cleaned_data.items() if k!='submission_key'}
        lines=[f.cleaned_data for f in formset if f.cleaned_data]
        lines=[{k:v for k,v in x.items() if k in LineFormSet.form._meta.fields and k not in ['request','id']} for x in lines]
        try:
            pr=services.create_pr(request.user,header,lines,form.cleaned_data['submission_key'])
            return redirect('pr-detail',pk=pr.pk)
        except (ValidationError,IntegrityError) as e: form.add_error(None,'รหัส PR / Source ID ซ้ำ หรือข้อมูลไม่ถูกต้อง' if isinstance(e,IntegrityError) else "; ".join(e.messages))
    return render(request,'work/create.html',{'form':form,'formset':formset})
@require('work','post')
def post(request,pk):
    pr=get_object_or_404(ProductionRequest,pk=pk)
    if request.method=='POST':
        try: services.post_pr(request.user,pk); messages.success(request,'เปิด PR แล้ว ขั้นตอนงานถูกบันทึกสำหรับแต่ละรายการ')
        except ValidationError as e: messages.error(request,'; '.join(e.messages))
        return redirect('pr-detail',pk=pk)
    return render(request,'confirm.html',{'title':f'เปิดงาน {pr.number}','description':'บันทึกชุดขั้นตอนงานจากแคตตาล็อก ณ เวลานี้ และเริ่มจ่ายงานได้'})

def event(request,formclass,title,callback,pr_id,context=None):
    form=formclass(request.POST or None,initial={'business_date':timezone.localdate()})
    if request.method=='POST' and form.is_valid():
        try:
            callback(form.cleaned_data); messages.success(request,'ลงรายการแล้ว'); return redirect('pr-detail',pk=pr_id)
        except (ValidationError,IntegrityError) as e: form.add_error(None,'คีย์รายการซ้ำหรือข้อมูลขัดกัน กรุณาตรวจสอบรายการเดิม' if isinstance(e,IntegrityError) else "; ".join(e.messages))
    return render(request,'form.html',{'form':form,'title':title,'description':context})
@require('work','post')
def assignment(request,pk):
    if not allowed(request.user,'work','lookup_catalog'): raise PermissionDenied
    ls=get_object_or_404(LineStep.objects.select_related('line__request','step'),pk=pk)
    def callback(d):
        d=dict(d); d['key']=d.pop('submission_key'); services.assign(request.user,ls,**d)
    return event(request,AssignmentForm,f'จ่ายงาน · {ls.line} · {ls.step.name}',callback,ls.line.request_id,f"ยังจ่ายได้ {services.progress(ls)['available']} ชิ้น · อัตราค่าแรงเลือกตามวันจ่ายงานและบันทึกคงที่ ไม่ใช่รายการชำระเงิน")
@require('work','post')
def receipt(request,pk):
    a=get_object_or_404(Assignment.objects.select_related('line_step__line__request','worker'),pk=pk)
    def callback(d):
        d=dict(d); d['key']=d.pop('submission_key'); services.receive(request.user,a,**d)
    return event(request,ReceiptForm,f'รับงาน / QC · {a.worker}',callback,a.line_step.line.request_id,f"อยู่กับช่าง {services.totals(a)['with_worker']} ชิ้น · งานส่งแก้ยังคงอยู่กับช่าง งานไม่ผ่านคืนเป็นจำนวนที่จ่ายทดแทนได้")
@require('work','post')
def delivery(request,pk):
    line=get_object_or_404(PRLine,pk=pk)
    def callback(d):
        d=dict(d); d['key']=d.pop('submission_key'); services.deliver(request.user,line,**d)
    return event(request,DeliveryForm,f'ส่งมอบ · {line}',callback,line.request_id,f'ส่งมอบได้ {services.deliverable(line)-services.delivered(line)} ชิ้น (ผ่าน QC ครบทุกขั้นตอน)')
@require('work','reverse')
def reverse(request,kind,pk):
    if kind not in ['assignment','receipt','delivery']: raise PermissionDenied
    obj=get_object_or_404({'assignment':Assignment,'receipt':QCReceipt,'delivery':Delivery}[kind],pk=pk)
    pr_id=obj.line.request_id if kind=='delivery' else (obj if kind=='assignment' else obj.assignment).line_step.line.request_id
    return event(request,ReasonForm,'ยืนยันกลับรายการ',lambda d:services.reverse(request.user,kind,pk,d['reason']),pr_id,'รายการเดิมจะคงอยู่ในประวัติ กรุณาตรวจสอบผลกระทบก่อนยืนยัน')
@require('work','post')
def close(request,pk,status):
    pr=get_object_or_404(ProductionRequest,pk=pk)
    return event(request,ReasonForm,'ปิด / ยกเลิก PR',lambda d:services.close_pr(request.user,pk,status,d['reason']),pr.pk)
@require('work')
def api_detail(request,pk):
    if request.method!='GET': return HttpResponse(status=405)
    pr=get_object_or_404(ProductionRequest,pk=pk)
    lines=[line_data(l,allowed(request.user,'work','read_financial')) for l in pr.lines.select_related('product')]
    for line in lines:
        line['deliveries']=[{'quantity':d.quantity,'date':d.business_date,'reference':d.reference,'reversed':bool(d.reversed_at)} for d in line['deliveries']]
        for step in line['steps']:
            for a in step['assignments']:
                a['receipts']=[{'id':str(r.pk),'accepted':r.accepted,'rejected':r.rejected,'rework':r.rework,'reversed':bool(r.reversed_at),'date':r.business_date} for r in a['receipts']]
    return JsonResponse({'id':str(pr.pk),'number':pr.number,'po_number':pr.po_number,'status':pr.status,'lines':lines})
def csv_safe(value):
    value=str(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r')) else value
@require('work','export')
def export(request):
    if not allowed(request.user,'work'): raise PermissionDenied
    financial=allowed(request.user,'work','read_financial')
    response=HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition']='attachment; filename="papradit-work.csv"'
    response.write('\ufeff'); writer=csv.writer(response)
    writer.writerow(['PR','PO','Job','Product','Size','Requested','Delivered','Remaining','Status','Due date','Step','Assigned','Accepted','With worker','Available']+(['Applied wage','Accepted-work reference value (not payable)'] if financial else []))
    try: rows=filtered(request)
    except ValidationError: return HttpResponse('Invalid date',status=400)
    for pr in rows:
        for line in pr.lines.select_related('product'):
            prefix=[pr.number,pr.po_number,str(pr.job),str(line.product),line.size,line.quantity,services.delivered(line),line.quantity-services.delivered(line),pr.status,pr.due_date]
            steps=list(line.steps.select_related('step'))
            if not steps: writer.writerow([csv_safe(v) for v in prefix]+['']*5+(['',''] if financial else []))
            for s in steps:
                p=services.progress(s)
                suffix=[str(s.step),p['assigned'],p['accepted'],p['with_worker'],p['available']]
                if financial:
                    active=s.assignments.filter(reversed_at__isnull=True)
                    rates='; '.join(str(a.unit_wage) for a in active)
                    value=sum((a.unit_wage*services.totals(a)['accepted'] for a in active),Decimal(0))
                    suffix += [rates,value]
                writer.writerow([csv_safe(v) for v in prefix+suffix])
    return response

@require('work','update_draft')
def edit_draft(request,pk):
    if not allowed(request.user,'work','lookup_catalog'): raise PermissionDenied
    pr=get_object_or_404(ProductionRequest,pk=pk)
    if pr.status!='draft': raise PermissionDenied
    form=HeaderForm(request.POST or None,instance=pr)
    form.fields.pop('submission_key')
    formset=LineFormSet(request.POST or None,instance=pr)
    for lf in formset:
        if lf.instance.pk and not lf.instance._state.adding:
            for field in ['source_pp_id','source_pr_list_id','source_ps_id']: lf.fields[field].disabled=True
    if request.method=='POST' and form.is_valid() and formset.is_valid():
        lines=[{k:v for k,v in f.cleaned_data.items() if k in list(LineFormSet.form._meta.fields)+['id'] and k!='request'} for f in formset if f.cleaned_data]
        try:
            services.update_pr(request.user,pr.pk,form.cleaned_data,lines)
            return redirect('pr-detail',pk=pk)
        except (ValidationError,IntegrityError) as e: form.add_error(None,'Source ID ซ้ำ' if isinstance(e,IntegrityError) else "; ".join(e.messages))
    return render(request,'work/create.html',{'form':form,'formset':formset,'editing':True})
