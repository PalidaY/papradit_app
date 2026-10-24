from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from core.permissions import allowed,audit,require
from .models import Product,Job,Worker,WorkStep,WageRate
from .forms import FORMS
REGISTRY={'products':('catalog.products','สินค้า'),'jobs':('catalog.jobs','งาน'),'patterns':('catalog.jobs','รูปแบบงาน'),'steps':('catalog.jobs','ขั้นตอนงาน'),'workers':('work','ช่าง / ผู้รับจ้าง'),'wages':('catalog.wages','ค่าแรง')}
@login_required
def listing(request,kind):
    if kind not in REGISTRY: raise PermissionDenied
    module,label=REGISTRY[kind]
    if not allowed(request.user,module): raise PermissionDenied
    if kind=='wages' and not allowed(request.user,module,'read_financial'): raise PermissionDenied
    model=FORMS[kind]._meta.model
    rows=model.objects.all()
    q=request.GET.get('q','')
    if q and kind!='wages': rows=rows.filter(Q(code__icontains=q)|Q(name__icontains=q))
    return render(request,'catalog/list.html',{'kind':kind,'label':label,'rows':rows,'q':q,'can_create':allowed(request.user,module,'create') and (kind!='wages' or allowed(request.user,module,'manage_prices')),'can_edit':kind!='wages' and allowed(request.user,module,'update_draft')})
@login_required
def edit(request,kind,pk=None):
    if kind not in REGISTRY: raise PermissionDenied
    module,label=REGISTRY[kind]
    if not allowed(request.user,module,'update_draft' if pk else 'create'): raise PermissionDenied
    if kind=='wages' and (pk or not allowed(request.user,module,'manage_prices') or not allowed(request.user,module,'read_financial')): raise PermissionDenied
    model=FORMS[kind]._meta.model
    instance=get_object_or_404(model,pk=pk) if pk else None
    before={} if not instance else {f:str(getattr(instance,f)) for f in FORMS[kind]._meta.fields}
    form=FORMS[kind](request.POST or None,instance=instance)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            item=form.save(commit=False)
            if kind=='wages':
                WorkStep.objects.select_for_update().get(pk=item.step_id)
                overlap=WageRate.objects.filter(step=item.step,price_type=item.price_type).filter(Q(effective_to__isnull=True)|Q(effective_to__gt=item.effective_from))
                if item.effective_to: overlap=overlap.filter(effective_from__lt=item.effective_to)
                if overlap.exists(): form.add_error(None,'ช่วงวันที่ซ้อนกับอัตราค่าแรงเดิม ให้ระบุวันสิ้นสุดก่อนเพิ่มอัตราใหม่')
                else: item.created_by=request.user
            if not form.errors:
                item.save()
                audit(request.user,'catalog.'+('create' if not pk else 'update'),item.pk,before=before,after={'kind':kind,**{f:str(getattr(item,f)) for f in FORMS[kind]._meta.fields}})
                messages.success(request,'บันทึกข้อมูลแล้ว'); return redirect('catalog-list',kind=kind)
    return render(request,'form.html',{'form':form,'title':f'{"แก้ไข" if pk else "เพิ่ม"} {label}'})
@login_required
def retire_rate(request,pk):
    if not all(allowed(request.user,'catalog.wages',a) for a in ['manage_prices','update_draft','read_financial']): raise PermissionDenied
    from django import forms
    class EndForm(forms.Form):
        effective_to=forms.DateField(label='สิ้นสุด (ไม่รวมวันนี้)',widget=forms.DateInput(attrs={'type':'date','class':'form-control'}))
    form=EndForm(request.POST or None)
    rate=get_object_or_404(WageRate,pk=pk)
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            WorkStep.objects.select_for_update().get(pk=rate.step_id)
            rate=WageRate.objects.select_for_update().get(pk=pk)
            end=form.cleaned_data['effective_to']
            if end<=rate.effective_from or rate.assignment_set.filter(business_date__gte=end).exists() or (rate.effective_to and end>rate.effective_to): form.add_error(None,'วันสิ้นสุดต้องหลังวันเริ่มต้น และไม่ตัดช่วงที่มีรายการจ่ายงานแล้ว')
            else:
                old=str(rate.effective_to); rate.effective_to=end; rate.save(update_fields=['effective_to'])
                audit(request.user,'catalog.end_rate',pk,before={'effective_to':old},after={'effective_to':str(end)})
                return redirect('catalog-list',kind='wages')
    return render(request,'form.html',{'form':form,'title':'กำหนดวันสิ้นสุดค่าแรง (ไม่แก้ไขยอดในอดีต)'})
@require('work','lookup_catalog')
def lookups(request):
    if not allowed(request.user,'work','lookup_catalog'): raise PermissionDenied
    return JsonResponse({'products':list(Product.objects.filter(active=True).values('id','code','name')),'jobs':list(Job.objects.filter(active=True).values('id','code','name')),'workers':list(Worker.objects.filter(active=True).values('id','code','name')),'steps':list(WorkStep.objects.filter(active=True).values('id','code','name','job_id'))})
