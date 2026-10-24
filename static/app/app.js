document.addEventListener('DOMContentLoaded',()=>{
 const add=document.getElementById('add-line');
 if(add) add.addEventListener('click',()=>{
  const total=document.getElementById('id_lines-TOTAL_FORMS');
  if(Number(total.value)>=100)return;
  const fragment=document.getElementById('empty-line').innerHTML.replaceAll('__prefix__',total.value);
  document.getElementById('line-forms').insertAdjacentHTML('beforeend',fragment);
  total.value=Number(total.value)+1;
 });
 document.body.addEventListener('htmx:responseError',()=>{
  const existing=document.getElementById('request-error');
  if(existing)existing.remove();
  const error=document.createElement('div');error.id='request-error';error.className='alert alert-danger';error.role='alert';error.textContent='โหลดข้อมูลไม่สำเร็จ กรุณาลองใหม่ หรือโหลดหน้าอีกครั้ง';
  document.getElementById('main').prepend(error);
 });
});
