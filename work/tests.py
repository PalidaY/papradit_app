import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections
from django.test import TestCase,TransactionTestCase,Client,override_settings
from django.urls import reverse
from django.utils import timezone
from catalog.models import Product,Job,WorkStep,Worker,WageRate
from core.models import ModuleGrant,AuditEvent,SourceIdentity
from .models import ProductionRequest,Assignment,QCReceipt,PRLine
from . import services
User=get_user_model()
class Fixture:
    def setup_data(self):
        self.user=User.objects.create_superuser('owner','owner@example.test','test-password-only-1984')
        self.day=timezone.localdate()
        self.product=Product.objects.create(code='0001',name='เสื้อ + ทดสอบ')
        self.job=Job.objects.create(code='J01',name='ลูกค้า + A')
        self.step=WorkStep.objects.create(code='S01',name='เย็บ',job=self.job)
        self.step2=WorkStep.objects.create(code='S02',name='รีด',job=self.job,sequence=2)
        self.worker=Worker.objects.create(code='W01',name='ช่าง + หนึ่ง')
        self.rate=WageRate.objects.create(step=self.step,amount='12.5000',effective_from=self.day,created_by=self.user)
        WageRate.objects.create(step=self.step2,amount='2.0000',effective_from=self.day,created_by=self.user)
        self.header={'number':'0001','po_number':'00002','job':self.job,'requester':'นิด + A','request_date':self.day,'due_date':self.day+timedelta(days=7)}
        self.pr=services.create_pr(self.user,self.header,[{'product':self.product,'size':'M','quantity':10,'source_pp_id':'0007','source_pr_list_id':'0008'},{'product':self.product,'size':'L','quantity':20}],uuid.uuid4())
        services.post_pr(self.user,self.pr.pk)
        self.line=self.pr.lines.get(size='M'); self.ls=self.line.steps.get(step=self.step); self.ls2=self.line.steps.get(step=self.step2)
    def assign(self,qty=10,ls=None,key=None):
        return services.assign(self.user,ls or self.ls,self.worker,qty,self.day,self.day+timedelta(days=2),'standard',key or uuid.uuid4())
    def receive(self,a,accepted=0,rejected=0,rework=0,key=None):
        return services.receive(self.user,a,self.day,accepted,rejected,rework,'test reason',key or uuid.uuid4())
@override_settings(SECURE_SSL_REDIRECT=False,SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class WorkTests(Fixture,TestCase):
    def setUp(self): self.setup_data()
    def test_event_date_inputs_are_iso_for_thai_locale(self):
        from .forms import AssignmentForm
        form=AssignmentForm(initial={'business_date':self.day})
        self.assertIn(f'value="{self.day.isoformat()}"',str(form['business_date']))
    def test_pr_form_post_and_draft_edit(self):
        self.client.force_login(self.user)
        data={'number':'FORM-0001','po_number':'001','job':str(self.job.pk),'context':'PPD','requester':'Test + ไทย','request_date':self.day.isoformat(),'due_date':self.header['due_date'].isoformat(),'submission_key':str(uuid.uuid4()),'lines-TOTAL_FORMS':'1','lines-INITIAL_FORMS':'0','lines-MIN_NUM_FORMS':'1','lines-MAX_NUM_FORMS':'100','lines-0-product':str(self.product.pk),'lines-0-size':'XL','lines-0-quantity':'15'}
        response=self.client.post(reverse('pr-create'),data)
        self.assertEqual(response.status_code,302)
        pr=ProductionRequest.objects.get(number='FORM-0001'); line=pr.lines.get()
        data.update({'requester':'Updated','lines-INITIAL_FORMS':'1','lines-0-id':str(line.pk),'lines-0-request':str(pr.pk),'lines-0-quantity':'16'})
        response=self.client.post(reverse('pr-edit',args=[pr.pk]),data)
        self.assertEqual(response.status_code,302)
        line.refresh_from_db(); self.assertEqual(line.quantity,16)
        pr.refresh_from_db(); self.assertEqual(pr.requester,'Updated')
    def test_delivery_reversal_retains_original(self):
        a=self.assign(); b=self.assign(ls=self.ls2); self.receive(a,5); self.receive(b,5)
        d=services.deliver(self.user,self.line,3,self.day,'D1',uuid.uuid4())
        services.reverse(self.user,'delivery',d.pk,'wrong document')
        d.refresh_from_db(); self.assertIsNotNone(d.reversed_at)
        self.assertEqual(services.delivered(self.line),0)

    def test_source_ids_and_distinct_sizes(self):
        self.assertEqual(self.pr.lines.count(),2); self.assertEqual(self.line.source_pp_id,'0007')
        self.assertEqual(SourceIdentity.objects.get(entity='pp_id').target_id,self.line.pk)
    def test_partial_qc_rework_and_replacement(self):
        a=self.assign(); self.receive(a,4,2,3)
        p=services.progress(self.ls)
        self.assertEqual((p['accepted'],p['with_worker'],p['available']),(4,4,2))
        self.assign(2)
        with self.assertRaises(ValidationError): self.assign(1)
        self.receive(a,4)
        self.assertEqual(services.totals(a)['with_worker'],0)
        self.assertEqual(services.totals(a)['received_attempts'],13)
    def test_sequential_steps_have_independent_limits(self):
        self.assign(); self.assign(ls=self.ls2)
        self.assertEqual(services.progress(self.ls2)['available'],0)
    def test_qc_overreceipt_and_reason_validation(self):
        a=self.assign(5)
        with self.assertRaises(ValidationError): self.receive(a,6)
        with self.assertRaises(ValidationError): services.receive(self.user,a,self.day,0,1,0,'',uuid.uuid4())
        self.assertEqual(QCReceipt.objects.count(),0)
    def test_duplicate_assignment_and_qc(self):
        key=uuid.uuid4(); a=self.assign(key=key); self.assertEqual(self.assign(key=key).pk,a.pk)
        with self.assertRaises(ValidationError): self.assign(qty=5,key=key)
        key=uuid.uuid4(); r=self.receive(a,4,key=key); self.assertEqual(self.receive(a,4,key=key).pk,r.pk)
        self.assertEqual(QCReceipt.objects.count(),1)
    def test_rate_and_label_changes_preserve_snapshot(self):
        a=self.assign(); self.rate.amount=99; self.rate.save()
        self.product.name='renamed'; self.product.save(); a.refresh_from_db()
        self.assertEqual(a.unit_wage,Decimal('12.5000')); self.assertEqual(a.line_step.line.product_id,self.product.pk)
    def test_missing_and_ambiguous_rate_fail_closed(self):
        self.rate.effective_from=self.day+timedelta(days=1); self.rate.save()
        with self.assertRaises(ValidationError): self.assign()
        self.rate.effective_from=self.day; self.rate.save()
        WageRate.objects.create(step=self.step,amount=20,effective_from=self.day,created_by=self.user)
        with self.assertRaises(ValidationError): self.assign()
    def test_partial_delivery_does_not_close_pr(self):
        a=self.assign(); b=self.assign(ls=self.ls2); self.receive(a,8); self.receive(b,6)
        d=services.deliver(self.user,self.line,4,self.day,'D01',uuid.uuid4())
        self.assertEqual(services.deliverable(self.line)-services.delivered(self.line),2)
        self.pr.refresh_from_db(); self.assertEqual(self.pr.status,'posted')
        with self.assertRaises(ValidationError): services.deliver(self.user,self.line,3,self.day,'D02',uuid.uuid4())
        self.assertEqual(self.line.deliveries.count(),1)
    def test_reverse_preserves_history_and_cannot_break_delivery(self):
        a=self.assign(); b=self.assign(ls=self.ls2); r=self.receive(a,5); self.receive(b,5)
        services.deliver(self.user,self.line,3,self.day,'D1',uuid.uuid4())
        with self.assertRaises(ValidationError): services.reverse(self.user,'receipt',r.pk,'correction')
        r.refresh_from_db(); self.assertIsNone(r.reversed_at)
        with self.assertRaises(ValidationError): services.reverse(self.user,'assignment',a.pk,'correction')
        c=self.assign(5,ls=self.pr.lines.get(size='L').steps.get(step=self.step))
        services.reverse(self.user,'assignment',c.pk,'wrong worker')
        c.refresh_from_db(); self.assertIsNotNone(c.reversed_at); self.assertTrue(Assignment.objects.filter(pk=c.pk).exists())
    def test_reverse_reject_cannot_overallocate(self):
        a=self.assign(); r=self.receive(a,rejected=5); self.assign(5)
        with self.assertRaises(ValidationError): services.reverse(self.user,'receipt',r.pk,'undo reject')
    def test_close_requires_complete_delivery(self):
        with self.assertRaises(ValidationError): services.close_pr(self.user,self.pr.pk,'closed','done')
    def test_post_snapshots_steps_and_is_idempotent(self):
        services.post_pr(self.user,self.pr.pk)
        self.assertEqual(self.line.steps.count(),2)
        WorkStep.objects.create(code='S03',name='new',job=self.job)
        self.assertEqual(self.line.steps.count(),2)
    def test_anonymous_denied_and_viewer_write_forbidden(self):
        url=reverse('pr-detail',args=[self.pr.pk])
        self.assertEqual(self.client.get(url).status_code,302)
        self.assertEqual(self.client.get(reverse('api-pr',args=[self.pr.pk])).status_code,401)
        self.assertEqual(self.client.get(reverse('lookups')).status_code,401)
        viewer=User.objects.create_user('viewer',password='only-test-very-long')
        ModuleGrant.objects.create(user=viewer,module='work',action='read')
        self.client.force_login(viewer)
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(self.client.post(reverse('pr-post',args=[self.pr.pk])).status_code,403)
        self.assertEqual(self.client.get(reverse('work-export')).status_code,403)
        self.assertEqual(self.client.get(reverse('catalog-list',args=['products'])).status_code,403)
        self.assertEqual(self.client.get(reverse('lookups')).status_code,403)
        self.assertEqual(self.client.get(reverse('users')).status_code,403)
        self.assertEqual(self.client.post(reverse('api-pr',args=[self.pr.pk])).status_code,405)
    def test_financial_data_absent_from_html_api_export(self):
        a=self.assign(); self.receive(a,4)
        operator=User.objects.create_user('operator',password='only-test-very-long')
        for action in ['read','export']: ModuleGrant.objects.create(user=operator,module='work',action=action)
        self.client.force_login(operator)
        response=self.client.get(reverse('api-pr',args=[self.pr.pk]))
        self.assertNotIn('unit_wage',response.json()['lines'][0]['steps'][0]['assignments'][0])
        self.assertNotContains(self.client.get(reverse('pr-detail',args=[self.pr.pk])),'12.5000')
        self.assertNotIn('Applied wage',self.client.get(reverse('work-export')).content.decode())
        ModuleGrant.objects.create(user=operator,module='work',action='read_financial')
        data=self.client.get(reverse('api-pr',args=[self.pr.pk])).json()
        self.assertIn('unit_wage',data['lines'][0]['steps'][0]['assignments'][0])
    def test_revocation_changes_next_request_and_disabled_user_loses_access(self):
        operator=User.objects.create_user('op',password='only-test-very-long')
        grant=ModuleGrant.objects.create(user=operator,module='work',action='read'); self.client.force_login(operator)
        self.assertEqual(self.client.get('/').status_code,200)
        grant.delete(); self.assertEqual(self.client.get('/').status_code,403)
        operator.is_active=False; operator.save(); self.assertEqual(self.client.get('/').status_code,302)
    def test_unreleased_modules_never_granted(self):
        from core.permissions import allowed
        self.assertFalse(allowed(self.user,'fabric'))
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/catalog/fabrics/').status_code,403)
    def test_catalog_overlap_rejected_and_price_end_guarded(self):
        self.client.force_login(self.user)
        resp=self.client.post(reverse('catalog-create',args=['wages']),{'step':self.step.pk,'amount':'100','effective_from':self.day.isoformat(),'price_type':'standard'})
        self.assertContains(resp,'ช่วงวันที่ซ้อน')
        self.assertEqual(WageRate.objects.filter(step=self.step).count(),1)
        a=self.assign()
        response=self.client.post(reverse('rate-end',args=[self.rate.pk]),{'effective_to':self.day.isoformat()})
        self.assertEqual(response.status_code,200); self.rate.refresh_from_db(); self.assertIsNone(self.rate.effective_to)
    def test_catalog_pages_forms_and_dashboard_render(self):
        self.client.force_login(self.user)
        for url in ['/', '/work/', '/work/new/', '/admin/users/', '/admin/audit/']+[f'/catalog/{kind}/' for kind in ['products','jobs','patterns','steps','workers','wages']]:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code,200)
    def test_csrf_required_for_writes(self):
        c=Client(enforce_csrf_checks=True); c.force_login(self.user)
        self.assertEqual(c.post(reverse('pr-post',args=[self.pr.pk])).status_code,403)
    def test_final_admin_protection_and_session_revocation(self):
        self.client.force_login(self.user)
        response=self.client.post(reverse('account',args=[self.user.pk]),{'revoke':'on'})
        self.assertContains(response,'ผู้ดูแลระบบคนสุดท้าย')
        self.user.refresh_from_db(); self.assertTrue(self.user.is_active)
        second=Client(); second.force_login(self.user); second.get('/')
        self.client.post(reverse('account',args=[self.user.pk]),{'is_active':'on','revoke':'on'})
        self.assertEqual(second.get('/').status_code,302)
    def test_login_throttling_no_auto_admin(self):
        for i in range(5): self.client.post('/accounts/login/',{'username':'unknown','password':'wrong'})
        self.assertEqual(self.client.post('/accounts/login/',{'username':'unknown','password':'wrong'}).status_code,429)
        self.assertEqual(User.objects.filter(is_superuser=True).count(),1)
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_invitation_uses_django_token_and_no_default_grants(self):
        from django.core import mail
        self.client.force_login(self.user)
        response=self.client.post(reverse('invite'),{'username':'newstaff','email':'staff@example.test'})
        self.assertEqual(response.status_code,302)
        target=User.objects.get(username='newstaff'); self.assertFalse(target.has_usable_password())
        self.assertFalse(ModuleGrant.objects.filter(user=target).exists()); self.assertEqual(len(mail.outbox),1)
        self.assertIn('/accounts/reset/',mail.outbox[0].body)
    def test_csv_formula_injection_escaped(self):
        self.pr.number='=1+2'; self.pr.save()
        self.client.force_login(self.user)
        self.assertIn("'=1+2",self.client.get(reverse('work-export')).content.decode())

class ConcurrentWorkTests(Fixture,TransactionTestCase):
    reset_sequences=True
    def setUp(self): self.setup_data()
    def race(self,fn):
        barrier=Barrier(2)
        def attempt(_):
            close_old_connections(); barrier.wait()
            try: fn(); return 'ok'
            except ValidationError: return 'rejected'
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool: return list(pool.map(attempt,range(2)))
    def test_concurrent_assignments_cannot_overallocate(self):
        result=self.race(lambda:self.assign(7))
        self.assertCountEqual(result,['ok','rejected']); self.assertEqual(Assignment.objects.count(),1)
    def test_concurrent_receipts_cannot_overreceive(self):
        a=self.assign(); result=self.race(lambda:self.receive(a,7))
        self.assertCountEqual(result,['ok','rejected']); self.assertEqual(services.totals(a)['accepted'],7)
    def test_concurrent_duplicate_submission_posts_once(self):
        key=uuid.uuid4(); result=self.race(lambda:self.assign(7,key=key))
        self.assertEqual(result,['ok','ok']); self.assertEqual(Assignment.objects.count(),1)
