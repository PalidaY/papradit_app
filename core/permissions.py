from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from .models import ModuleGrant, MODULES
RELEASED = {'admin','work','catalog.products','catalog.jobs','catalog.wages'}
def allowed(user,module,action='read'):
    if not user.is_authenticated or not user.is_active or module not in RELEASED:
        return False
    if user.is_superuser:
        return True
    return ModuleGrant.objects.filter(Q(user=user)|Q(group__in=user.groups.all()),module=module,action=action).exists()
def require(module,action='read'):
    def decorator(view):
        @wraps(view)
        def wrapped(request,*args,**kwargs):
            if not request.user.is_authenticated:
                if request.path.startswith('/api/'):
                    return JsonResponse({'error':'Authentication required'},status=401)
                return redirect_to_login(request.get_full_path())
            if not allowed(request.user,module,action):
                if request.path.startswith('/api/'):
                    return JsonResponse({'error':'Forbidden'},status=403)
                raise PermissionDenied
            return view(request,*args,**kwargs)
        return wrapped
    return decorator
def navigation(request):
    return {'module_navigation':[{'key':key,'label':label,'released':key in RELEASED,'allowed':allowed(request.user,key)} for key,label in MODULES], 'can_financial':allowed(request.user,'work','read_financial'), 'can_users':allowed(request.user,'admin','manage_users'), 'can_grants':allowed(request.user,'admin','manage_permissions')}
def audit(actor,action,target,before=None,after=None):
    from .models import AuditEvent
    return AuditEvent.objects.create(actor=actor,action=action,target=str(target),before=before or {},after=after or {})
