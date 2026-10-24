from django.contrib.auth import logout
from .models import AccountState
class SessionPolicyMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if request.user.is_authenticated:
            state,_ = AccountState.objects.get_or_create(user=request.user)
            version = request.session.get('account_version')
            if version is None: request.session['account_version']=state.session_version
            elif version != state.session_version or not request.user.is_active: logout(request)
        return self.get_response(request)
