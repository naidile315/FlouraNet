// cart.js: handles quantity changes in the cart and updates totals via AJAX

(function(){
  function qs(selector, el=document){ return el.querySelector(selector); }
  function qsa(selector, el=document){ return Array.from(el.querySelectorAll(selector)); }

  const updateUrl = '/cart/update-quantity/';

  function sendUpdate(itemId, quantity){
    return fetch(updateUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify({ item_id: itemId, quantity: quantity })
    }).then(r => r.json());
  }

  function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
  }

  function onQtyChange(itemId, newQty, inputEl){
    sendUpdate(itemId, newQty).then(resp => {
      if(!resp) return;
      if(resp.status !== 'ok'){
        console.error('Cart update error', resp);
        return;
      }
      if(resp.action === 'deleted'){
        // remove the item row
        const row = document.querySelector('[data-item-id="'+itemId+'"]');
        if(row) row.remove();
        // update total if present
        const totalEl = qs('#cart-total');
        if(totalEl) totalEl.textContent = resp.total;
        return;
      }
      // update item total and overall total
      const itemTotalEl = qs('#item-total-' + itemId);
      if(itemTotalEl) itemTotalEl.textContent = resp.item_total;
      const totalEl = qs('#cart-total');
      if(totalEl) totalEl.textContent = resp.total;
    }).catch(err => console.error('Failed to update cart', err));
  }

  document.addEventListener('click', function(e){
    const dec = e.target.closest('.qty-decrease');
    const inc = e.target.closest('.qty-increase');
    if(dec){
      const id = dec.getAttribute('data-item-id');
      const input = document.querySelector('.qty-input[data-item-id="'+id+'"]');
      if(!input) return;
      let val = parseInt(input.value) || 1;
      val = Math.max(1, val - 1);
      input.value = val;
      onQtyChange(id, val, input);
    }
    if(inc){
      const id = inc.getAttribute('data-item-id');
      const input = document.querySelector('.qty-input[data-item-id="'+id+'"]');
      if(!input) return;
      let val = parseInt(input.value) || 1;
      val = val + 1;
      input.value = val;
      onQtyChange(id, val, input);
    }
  });

  document.addEventListener('change', function(e){
    const input = e.target.closest('.qty-input');
    if(!input) return;
    const id = input.getAttribute('data-item-id');
    let val = parseInt(input.value) || 1;
    if(val < 1) val = 1;
    input.value = val;
    onQtyChange(id, val, input);
  });

})();
