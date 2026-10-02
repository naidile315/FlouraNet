// auth.js — manage recently used usernames for login UX
document.addEventListener('DOMContentLoaded', function(){
  try{
    var storageKey = 'flouranet_recent_users';
    var rememberKey = 'flouranet_remembered_user';
    var form = document.querySelector('form');
    var usernameInput = document.querySelector('input[name="username"]');
    var passwordInput = document.querySelector('input[name="password"]');
    if(!usernameInput) return;

    // create list container
    var listWrap = document.createElement('div');
    listWrap.className = 'recent-creds-wrap';
    var listEl = document.createElement('ul');
    listEl.className = 'recent-creds-list';
    listWrap.appendChild(listEl);
    var parentBox = usernameInput.closest('.input-group') ? usernameInput.closest('.input-group').parentNode : usernameInput.parentNode;
    parentBox.appendChild(listWrap);

    function loadList(){
      var raw = localStorage.getItem(storageKey) || '[]';
      try{ return JSON.parse(raw); }catch(e){ return []; }
    }
    function saveList(arr){ localStorage.setItem(storageKey, JSON.stringify(arr.slice(0,5))); }

    function render(){
      var items = loadList();
      listEl.innerHTML = '';
      if(!items || items.length === 0) { listWrap.style.display='none'; return; }
      listWrap.style.display='block';
      items.forEach(function(u){
        var li = document.createElement('li');
        li.className = 'recent-creds-item';
        li.textContent = u;
        li.addEventListener('click', function(){
          usernameInput.value = u;
          usernameInput.dispatchEvent(new Event('input'));
          if(passwordInput) passwordInput.focus();
        });
        listEl.appendChild(li);
      });
      var clear = document.createElement('li');
      clear.className = 'recent-creds-clear';
      clear.innerHTML = '<small>Clear recent</small>';
      clear.addEventListener('click', function(){ localStorage.removeItem(storageKey); render(); });
      listEl.appendChild(clear);
    }

    // if a username was remembered previously, prefill
    try{
      var remembered = localStorage.getItem(rememberKey);
      if(remembered && (!usernameInput.value || usernameInput.value.trim()==='')){
        usernameInput.value = remembered;
        if(passwordInput) passwordInput.focus();
      }
    }catch(e){}

    // show list when input focused and there are items
    usernameInput.addEventListener('focus', render);
    usernameInput.addEventListener('input', function(){
      // simple filter
      var filter = usernameInput.value.toLowerCase();
      var items = listEl.querySelectorAll('.recent-creds-item');
      items.forEach(function(it){ it.style.display = it.textContent.toLowerCase().indexOf(filter)===-1 ? 'none' : 'block'; });
      listWrap.style.display = listEl.children.length ? 'block' : 'none';
    });

    // store username on submit (optimistic — saves value entered)
    if(form){
      form.addEventListener('submit', function(){
        var v = (usernameInput.value || '').trim();
        if(!v) return;
        var arr = loadList();
        // remove duplicates
        arr = arr.filter(function(a){ return a !== v; });
        arr.unshift(v);
        saveList(arr);

        // remember username if user asked
        try{
          var rememberEl = form.querySelector('input[name="remember"]');
          if(rememberEl && rememberEl.checked){ localStorage.setItem(rememberKey, v); }
          else { localStorage.removeItem(rememberKey); }
        }catch(e){}
      });
    }

    // render initially if input has focus
    if(document.activeElement === usernameInput) render();
  }catch(e){ console.error('auth.js error', e); }
});
