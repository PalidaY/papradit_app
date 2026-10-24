"""Opt-in browser suite: python manage.py test work.browser_journeys.
Requires separately locked dev dependencies and a Chromium executable.
All data lives in Django's disposable PostgreSQL test database.
"""
import os
from pathlib import Path
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from playwright.sync_api import sync_playwright, expect
from .tests import Fixture
from .models import ProductionRequest

@override_settings(SECURE_SSL_REDIRECT=False,SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False,STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class BrowserJourneys(Fixture,StaticLiveServerTestCase):
    def setUp(self): self.setup_data()
    def test_operator_journey_and_responsive_layout(self):
        artifacts=Path('.test-artifacts'); artifacts.mkdir(exist_ok=True)
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH') or None,headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':1050})
            errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('response',lambda r:errors.append(f'HTTP {r.status}: {r.url}') if r.status>=400 else None)
            page.goto(self.live_server_url+'/')
            page.locator('#id_username').fill('owner'); page.locator('#id_password').fill('test-password-only-1984')
            page.get_by_role('button',name='เข้าสู่ระบบ').click()
            page.wait_for_url(self.live_server_url+'/')
            self.assertEqual(page.locator('h1').inner_text(),'ภาพรวมการทำงาน.')
            page.get_by_role('link',name='＋ รับ PR ใหม่').click()
            page.locator('#id_number').fill('UI-0002')
            page.locator('#id_po_number').fill('00003')
            page.locator('#id_job').select_option(str(self.job.pk))
            page.locator('#id_requester').fill('ผู้ขอ + ทดสอบ')
            page.locator('#id_request_date').fill(self.day.isoformat())
            page.locator('#id_due_date').fill(self.header['due_date'].isoformat())
            for i,size,qty in [(0,'M','10'),(1,'L','20')]:
                page.locator(f'#id_lines-{i}-product').select_option(str(self.product.pk))
                page.locator(f'#id_lines-{i}-size').fill(size)
                page.locator(f'#id_lines-{i}-quantity').fill(qty)
            page.get_by_role('button',name='บันทึกร่าง PR').click()
            page.wait_for_load_state('networkidle')
            self.assertNotIn('/new/',page.url,msg=str(page.locator('.errorlist').all_text_contents())+str(page.locator(':invalid').evaluate_all('(els)=>els.map(e=>({name:e.name,message:e.validationMessage,value:e.value}))')))
            page.get_by_role('link',name='เปิดงาน →').click(); page.get_by_role('button',name='ยืนยันเปิดงาน').click()
            page.get_by_role('link',name='＋ จ่ายงาน').first.click()
            page.locator('#id_worker').select_option(str(self.worker.pk))
            page.locator('#id_quantity').fill('11')
            page.locator('#id_due_date').fill(self.header['due_date'].isoformat())
            page.get_by_role('button',name='บันทึก / ยืนยัน').click()
            expect(page.locator('.errorlist')).to_be_visible()
            page.locator('#id_quantity').fill('10'); page.get_by_role('button',name='บันทึก / ยืนยัน').click()
            page.get_by_role('link',name='รับ / QC').first.click()
            page.locator('#id_accepted').fill('3'); page.locator('#id_rework').fill('2'); page.locator('#id_note').fill('ส่งแก้ตะเข็บ')
            page.get_by_role('button',name='บันทึก / ยืนยัน').click()
            page.get_by_text('ผ่าน 3 / ไม่ผ่าน 0 / ส่งแก้ 2',exact=False).wait_for()
            self.assertIn('อยู่กับช่าง 7',page.locator('.step-metrics').first.inner_text())
            page.goto(self.live_server_url+'/work/?q=UI-0002')
            self.assertEqual(page.locator('.record-link').count(),1)
            page.locator('#q').fill('0001'); page.get_by_role('button',name='ค้นหา',exact=True).click()
            page.wait_for_url('**q=0001**')
            self.assertEqual(page.locator('.record-link').first.inner_text(),'0001')
            page.goto(self.live_server_url+'/')
            self.assertEqual(page.locator('.sidebar').evaluate('(el)=>getComputedStyle(el).width'),'250px')
            self.assertTrue(page.evaluate("typeof htmx !== 'undefined'"))
            page.screenshot(path=str(artifacts/'dashboard-desktop.png'),full_page=True)
            page.set_viewport_size({'width':768,'height':1024})
            self.assertTrue(page.locator('h1').is_visible())
            self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),768)
            page.screenshot(path=str(artifacts/'dashboard-tablet.png'),full_page=True)
            self.assertEqual(errors,[])
            browser.close()
        self.assertEqual(ProductionRequest.objects.get(number='UI-0002').lines.count(),2)
