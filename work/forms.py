import uuid
from django import forms
from django.forms import inlineformset_factory
from catalog.forms import StyledForm
from catalog.models import Product,Job,Worker
from .models import ProductionRequest,PRLine
class HeaderForm(StyledForm):
    submission_key=forms.UUIDField(widget=forms.HiddenInput,initial=uuid.uuid4)
    class Meta:
        model=ProductionRequest
        fields=['number','po_number','pi_number','job','context','requester','request_date','due_date']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.fields['job'].queryset=Job.objects.filter(active=True)
class LineForm(StyledForm):
    class Meta:
        model=PRLine
        fields=['product','size','quantity','fabric_reference','color','source_pp_id','source_pr_list_id','source_ps_id']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.fields['product'].queryset=Product.objects.filter(active=True)
LineFormSet=inlineformset_factory(ProductionRequest,PRLine,form=LineForm,extra=3,min_num=1,validate_min=True,max_num=100,validate_max=True,can_delete=False)
class EventForm(forms.Form):
    submission_key=forms.UUIDField(widget=forms.HiddenInput,initial=uuid.uuid4)
    business_date=forms.DateField(label='วันที่ทำรายการ',widget=forms.DateInput(attrs={'type':'date'}))
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            field.widget.attrs['class']='form-control'
            if isinstance(field,forms.DateField): field.widget=forms.DateInput(format='%Y-%m-%d',attrs={'type':'date','class':'form-control'})
class AssignmentForm(EventForm):
    worker=forms.ModelChoiceField(label='ช่าง / ผู้รับจ้าง',queryset=Worker.objects.filter(active=True))
    quantity=forms.IntegerField(label='จำนวนจ่าย',min_value=1)
    due_date=forms.DateField(label='กำหนดส่ง',widget=forms.DateInput(attrs={'type':'date'}))
    payment_due_date=forms.DateField(label='กำหนดชำระ (ข้อมูลอ้างอิง)',required=False,widget=forms.DateInput(attrs={'type':'date'}))
    price_type=forms.CharField(label='ประเภทค่าแรง',initial='standard',max_length=40)
class ReceiptForm(EventForm):
    accepted=forms.IntegerField(label='ผ่าน QC',min_value=0,initial=0)
    rejected=forms.IntegerField(label='ไม่ผ่าน / ออกจากงาน (จ่ายทดแทนได้)',min_value=0,initial=0)
    rework=forms.IntegerField(label='ส่งแก้ / ยังอยู่กับช่าง',min_value=0,initial=0)
    note=forms.CharField(label='หมายเหตุ / เหตุผล',widget=forms.Textarea,required=False)
class DeliveryForm(EventForm):
    quantity=forms.IntegerField(label='จำนวนส่งมอบ',min_value=1)
    reference=forms.CharField(label='เอกสารอ้างอิง',max_length=100)
class ReasonForm(forms.Form):
    reason=forms.CharField(label='เหตุผล',widget=forms.Textarea(attrs={'class':'form-control'}))
