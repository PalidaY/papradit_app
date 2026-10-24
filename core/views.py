import hashlib
from datetime import timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model,logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm,PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView,PasswordResetView
from django.core.exceptions import PermissionDenied,ValidationError
from django.core.mail import send_mail
from django.db import transaction,connection
from django.http import JsonResponse
from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.conf import settings
from .models import ModuleGrant,AccountState,LoginThrottle,AuditEvent,MODULES,ACTIONS
from .permissions import require,allowed,audit
User=get_user_model()

def throttle_key(request,scope):
    identity=request.POST.get('username',request.POST.get('email','')).casefold().strip()
    # Both per-account and per-address buckets are checked below; no untrusted forwarding headers.
    return [hashlib.sha256(f'{scope}:account:{identity}'.encode()).hexdigest(),hashlib.sha256(f'{scope}:ip:{request.META.get("REMOTE_ADDR","")}'.encode()).hexdigest()]

def throttled(request,scope):
    now=timezone.now()
    blocked=False
    with transaction.atomic():
        for key in sorted(throttle_key(request,scope)):
            LoginThrottle.objects.get_or_create(key=key,defaults={'window_start':now})
            row=LoginThrottle.objects.select_for_update().get(pk=key)
            if row.window_start<now-timedelta(minutes=15): row.failures=0; row.window_start=now
            if row.failures>=5: blocked=True
            row.failures+=1; row.save()
    return blocked
class ThrottledLogin(LoginView):
    template_name='registration/login.html'
    def post(self,request,*args,**kwargs):
        if throttled(request,'login'):
            form=self.get_form(); form.add_error(None,'ลองใหม่อีกครั้งใน 15 นาที')
            return self.render_to_response(self.get_context_data(form=form),status=429)
        return super().post(request,*args,**kwargs)
    def form_valid(self,form):
        response=super().form_valid(form)
        state,_=AccountState.objects.get_or_create(user=self.request.user)
        self.request.session['account_version']=state.session_version
        return response
class ThrottledReset(PasswordResetView):
    template_name='registration/password_reset_form.html'
    email_template_name='registration/password_reset_email.txt'
    subject_template_name='registration/password_reset_subject.txt'
    def post(self,request,*args,**kwargs):
        if throttled(request,'reset'): return JsonResponse({'error':'Please try again in 15 minutes.'},status=429)
        return super().post(request,*args,**kwargs)
def health(request):
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1'); cursor.fetchone()
    except Exception: return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ok'})
class InviteForm(forms.Form):
    username=forms.CharField(label='ชื่อบัญชี',max_length=150)
    email=forms.EmailField(label='อีเมล')
class AccountForm(forms.Form):
    is_active=forms.BooleanField(label='อนุญาตให้เข้าสู่ระบบ',required=False)
    revoke=forms.BooleanField(label='เพิกถอนเซสชันทั้งหมด',required=False)
class GrantForm(forms.Form):
    module=forms.ChoiceField(choices=MODULES,label='โมดูล')
    action=forms.ChoiceField(choices=ACTIONS,label='สิทธิ์')
    remove=forms.BooleanField(required=False,label='ถอนสิทธิ์ (ถ้าไม่เลือก = เพิ่ม)')

def style(form):
    for f in form.fields.values(): f.widget.attrs['class']='form-check-input' if isinstance(f.widget,forms.CheckboxInput) else 'form-control'
    return form
@login_required
def users(request):
    if not (allowed(request.user,'admin','manage_users') or allowed(request.user,'admin','manage_permissions')): raise PermissionDenied
    return render(request,'core/users.html',{'users':User.objects.order_by('username')})
@require('admin','manage_users')
def invite(request):
    form=style(InviteForm(request.POST or None))
    if request.method=='POST' and form.is_valid():
        if User.objects.filter(username=form.cleaned_data['username']).exists() or User.objects.filter(email__iexact=form.cleaned_data['email']).exists(): form.add_error(None,'ชื่อบัญชีหรืออีเมลมีอยู่แล้ว')
        else:
            with transaction.atomic():
                user=User.objects.create_user(**form.cleaned_data)
                user.set_unusable_password(); user.save()
                AccountState.objects.create(user=user)
                audit(request.user,'admin.invite',user.pk,after={'username':user.username,'active':True})
                uid=urlsafe_base64_encode(force_bytes(user.pk)); token=default_token_generator.make_token(user)
                url=settings.PUBLIC_BASE_URL+reverse('password_reset_confirm',kwargs={'uidb64':uid,'token':token})
                # Fail closed: no successful invitation/account if email delivery fails.
                try: send_mail('Papradit — ตั้งรหัสผ่านบัญชีของคุณ',f'ตั้งรหัสผ่านภายใน 1 ชั่วโมง: {url}',settings.DEFAULT_FROM_EMAIL,[user.email],fail_silently=False)
                except Exception:
                    transaction.set_rollback(True); form.add_error(None,'ส่งอีเมลไม่สำเร็จ กรุณาตรวจสอบการตั้งค่า SMTP')
                else:
                    messages.success(request,'ส่งคำเชิญแล้ว บัญชียังไม่มีสิทธิ์เข้าถึงโมดูลจนกว่าจะได้รับสิทธิ์'); return redirect('users')
    return render(request,'form.html',{'form':form,'title':'เชิญผู้ใช้','description':'บัญชีใหม่ไม่มีสิทธิ์โดยอัตโนมัติ ลิงก์ตั้งรหัสผ่านส่งทางอีเมล ไม่มีการสมัครบัญชีสาธารณะ'})
@require('admin','manage_users')
def account(request,pk):
    target=get_object_or_404(User,pk=pk)
    form=style(AccountForm(request.POST or None,initial={'is_active':target.is_active}))
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            # All privileged account changes serialize on the full administrator set.
            list(User.objects.select_for_update().filter(is_superuser=True).order_by('pk'))
            target=User.objects.select_for_update().get(pk=pk)
            if target.is_superuser and not request.user.is_superuser: raise PermissionDenied
            active=form.cleaned_data['is_active']
            if target.is_superuser and target.is_active and not active and User.objects.filter(is_superuser=True,is_active=True).count()<=1: form.add_error(None,'ไม่สามารถปิดผู้ดูแลระบบคนสุดท้าย')
            else:
                before={'is_active':target.is_active}; target.is_active=active; target.save(update_fields=['is_active'])
                state,_=AccountState.objects.select_for_update().get_or_create(user=target)
                if not active or form.cleaned_data['revoke']: state.session_version+=1; state.save()
                audit(request.user,'admin.account',target.pk,before=before,after={'is_active':active,'revoked':bool(not active or form.cleaned_data['revoke'])})
                return redirect('users')
    return render(request,'form.html',{'form':form,'title':f'บัญชี · {target.username}'})
@require('admin','manage_permissions')
def grants(request,pk):
    target=get_object_or_404(User,pk=pk)
    if target.is_superuser and not request.user.is_superuser: raise PermissionDenied
    form=style(GrantForm(request.POST or None))
    if request.method=='POST' and form.is_valid():
        d=form.cleaned_data
        # A delegated administrator cannot mint permissions they do not hold.
        if not request.user.is_superuser and not allowed(request.user,d['module'],d['action']): raise PermissionDenied
        with transaction.atomic():
            if d['remove']: ModuleGrant.objects.filter(user=target,module=d['module'],action=d['action']).delete()
            else: ModuleGrant.objects.get_or_create(user=target,module=d['module'],action=d['action'])
            audit(request.user,'admin.permission',target.pk,after={'module':d['module'],'action':d['action'],'removed':d['remove']})
            return redirect('grants',pk=pk)
    matrix=[{'module':key,'label':label,'actions':[a for a,_ in ACTIONS if allowed(target,key,a)]} for key,label in MODULES]
    return render(request,'core/grants.html',{'form':form,'target':target,'matrix':matrix})
@require('admin')
def audit_log(request):
    from django.core.paginator import Paginator
    events=AuditEvent.objects.select_related('actor')
    # Audit records can contain prices/account metadata. Only explicit financial + admin access sees payloads.
    payloads=allowed(request.user,'admin','read_financial')
    return render(request,'core/audit.html',{'page':Paginator(events,50).get_page(request.GET.get('page')),'payloads':payloads})

@require('admin','manage_permissions')
def roles(request):
    from django.contrib.auth.models import Group
    class RoleForm(forms.Form):
        name=forms.CharField(label='ชื่อบทบาท',max_length=150)
        module=forms.ChoiceField(choices=MODULES,label='โมดูล')
        action=forms.ChoiceField(choices=ACTIONS,label='สิทธิ์')
        remove=forms.BooleanField(label='ถอนสิทธิ์',required=False)
    form=style(RoleForm(request.POST or None))
    if request.method=='POST' and form.is_valid():
        d=form.cleaned_data
        if not request.user.is_superuser and not allowed(request.user,d['module'],d['action']): raise PermissionDenied
        with transaction.atomic():
            group,_=Group.objects.get_or_create(name=d['name'])
            if d['remove']: ModuleGrant.objects.filter(group=group,module=d['module'],action=d['action']).delete()
            else: ModuleGrant.objects.get_or_create(group=group,module=d['module'],action=d['action'])
            audit(request.user,'admin.role',group.pk,after=d)
        return redirect('roles')
    return render(request,'core/roles.html',{'form':form,'roles':[{'name':g.name,'grants':list(ModuleGrant.objects.filter(group=g))} for g in Group.objects.order_by('name')]})
@require('admin','manage_permissions')
def membership(request,pk):
    from django.contrib.auth.models import Group
    class MembershipForm(forms.Form):
        groups=forms.ModelMultipleChoiceField(queryset=Group.objects.order_by('name'),label='บทบาท',required=False)
    target=get_object_or_404(User,pk=pk)
    if target.is_superuser and not request.user.is_superuser: raise PermissionDenied
    form=style(MembershipForm(request.POST if request.method=='POST' else None,initial={'groups':target.groups.all()}))
    if request.method=='POST' and form.is_valid():
        groups=form.cleaned_data['groups']
        old_groups=target.groups.all()
        changed=set(groups.values_list('pk',flat=True)) ^ set(old_groups.values_list('pk',flat=True))
        for grant in ModuleGrant.objects.filter(group_id__in=changed):
            if not request.user.is_superuser and not allowed(request.user,grant.module,grant.action): raise PermissionDenied
        with transaction.atomic():
            before=list(target.groups.values_list('name',flat=True)); target.groups.set(groups)
            audit(request.user,'admin.membership',target.pk,before={'roles':before},after={'roles':list(groups.values_list('name',flat=True))})
        return redirect('users')
    return render(request,'form.html',{'form':form,'title':f'บทบาท · {target.username}'})
