from django import forms
from .models import Product, Job, Pattern, Worker, WorkStep, WageRate
class StyledForm(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            field.widget.attrs['class']='form-check-input' if isinstance(field.widget,forms.CheckboxInput) else 'form-control'
            if isinstance(field,forms.DateField): field.widget=forms.DateInput(attrs={'type':'date','class':'form-control'},format='%Y-%m-%d')
def factory(model,fields):
    return forms.modelform_factory(model,form=StyledForm,fields=fields)
FORMS={
'products':factory(Product,['code','name','category','active']),
'jobs':factory(Job,['code','name','description','active']),
'patterns':factory(Pattern,['code','name','active']),
'workers':factory(Worker,['code','name','kind','contact','active']),
'steps':factory(WorkStep,['code','name','job','pattern','sequence','active']),
'wages':factory(WageRate,['step','amount','effective_from','effective_to','price_type']),
}
