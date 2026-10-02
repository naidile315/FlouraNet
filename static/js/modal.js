document.addEventListener('DOMContentLoaded', function(){
  const modalEl = document.getElementById('plantModal');
  if(!modalEl) return;
  const modal = new bootstrap.Modal(modalEl);
  document.querySelectorAll('[data-plant-name]').forEach(el=>{
    el.addEventListener('click', function(e){
      e.preventDefault();
      const name = this.getAttribute('data-plant-name');
      const desc = this.getAttribute('data-plant-desc');
      const price = this.getAttribute('data-plant-price');
      const img = this.getAttribute('data-plant-img');
      const link = this.getAttribute('data-plant-link');
      document.getElementById('plantModalLabel').textContent = name;
      document.getElementById('plantModalName').textContent = name;
      document.getElementById('plantModalDesc').textContent = desc || '';
      document.getElementById('plantModalPrice').textContent = price ? '₹'+price : '';
      const imgEl = document.getElementById('plantModalImage');
      if(img){ imgEl.src = img; imgEl.style.display='block'; } else { imgEl.style.display='none'; }
      const detailLink = document.getElementById('plantModalDetailLink');
      detailLink.href = link || '#';
      modal.show();
    });
  });
});
