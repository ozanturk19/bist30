/* ─────────────────────────────────────────────────────────────────────────
   K-O (CANLI) — Klavye odak görünürlüğü denetçisi · WCAG 2.4.7 Focus Visible (AA)
   21.09 (CPO). Pre-deploy KAPISI DEĞİL: ihlal statik CSS'te görülemez.
   ÖLÇÜLMESİ GEREKEN: öğe odaklanınca GÖRÜNÜM GERÇEKTEN DEĞİŞİYOR MU.

   İKİ İHLAL SINIFI
     A) İmza hiç değişmiyor (veya yalnız outline-color değişip style:none kalıyor)
     B) Halka çiziliyor AMA ata kutusu kirpıyor — outline KUTUNUN DIŞINA çizilir,
        `overflow` visible değilse boğulur. 21.09'da gerçek bulgu bu sınıftan çıktı.

   ⚠️ HARNESS GEÇERLİLİĞİ — İKİ ŞART, İKİSİ DE ZORUNLU
   1) `:focus-visible` yalnız KLAVYE modalitesinde eşleşir. Betikten önce sayfada
      GERÇEK bir Tab'a basılmalı: computer{action:"key",text:"Tab"}. Sentetik
      KeyboardEvent modaliteyi DEĞİŞTİRMEZ (untrusted). Betik bunu kendi doğrular.
   2) ⛔ TRANSITION ÖLDÜRÜLMELİ. `.bp-nav-item`de `transition:...border-color .15s`
      var; `focus()` sonrası AYNI TİCK okunan getComputedStyle geçişin BAŞLANGICINI
      verir (21.09'da 6px macenta halka `4px` olarak, sonraki karede `5.5px`
      okundu). Ölçümden önce `*{transition-duration:0s!important}` enjekte edilir.

   ⛔ GEOMETRİ TEK BAŞINA KANIT DEĞİL — `.th-sort-btn < #tableWrap` room=0 verdi ama
   6px macenta probu ekran görüntüsünde TAM GÖRÜNÜYORDU (yanlış pozitif). Aday çıkan
   her sınıf BOYAMA testiyle doğrulanmalı: aynı halkayı devasa/parlak yap, yalnız
   `overflow`u değiştirip A/B ekran görüntüsü al. (Browser pane'de zoom kırpma
   çalışmıyor; 1024 CSS px dpr=2 render 800px'e inerken ince yaylar kaybolur —
   6px değil 20px prob kullan.)

   ⛔ BU DEDEKTÖRÜN BİLİNEN EKSİĞİ: B sınıfı yalnız "değişen özellikler outline
   ALT KÜMESİ" ise çalışır. Öğe odakta başka bir şey de değiştiriyorsa (ata
   kaydırma, arka plan) atlanır — 21.09'da anasayfada nav öğeleri B/P'ye HIÇ
   düşmedi, oysa doğrudan ölçümde 5/5 öğede ust=alt=0 (gereken 4) çıktı.
   Şüphelenilen bileşen için DOĞRUDAN room ölçümü yap, sweep sayısına güvenme.

   Kullanım: sayfayı aç → Tab'a bas → bu dosyanın gövdesini javascript_tool ile
   çalıştır. Çıktı: {page,cand,A,Aagg,B,Bagg,P,Pagg}. Hedef: A=0, B=0.
   ──────────────────────────────────────────────────────────────────── */
(async () => {
const k=document.createElement('style');k.textContent='*,*::before,*::after{transition-duration:0s !important;animation-duration:0s !important}';document.head.appendChild(k);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
const SEL='a[href],button,input:not([type=hidden]),select,textarea,summary,[role="button"],[role="tab"],[role="link"],[tabindex]';const OUT=['outline-style','outline-width','outline-color','outline-offset'];const OTHER=['box-shadow','background-color','background-image','color','border-top-width','border-right-width','border-bottom-width','border-left-width','border-top-color','border-right-color','border-bottom-color','border-left-color','text-decoration-line','filter','opacity','transform','position','top','left','width','height','visibility','clip-path'];
function snap(e){const o={},c=getComputedStyle(e);for(const p of OUT.concat(OTHER))o[p]=c.getPropertyValue(p);for(const q of ['::before','::after']){const z=getComputedStyle(e,q);for(const p of ['content','box-shadow','background-color','outline-style','width','height','opacity','transform'])o[q+p]=z.getPropertyValue(p);}let a=e.parentElement,d=0;while(a&&d<2){const z=getComputedStyle(a);for(const p of OUT.concat(OTHER))o['^'+d+p]=z.getPropertyValue(p);a=a.parentElement;d++;}return o;}
function cl(e){let a=e.parentElement;while(a&&a!==document.documentElement){const c=getComputedStyle(a);if((c.overflowX!=='visible'||c.overflowY!=='visible')&&a!==document.body)return a;a=a.parentElement;}return null;}
function L(e){let s=e.tagName.toLowerCase();if(e.id)s+='#'+e.id;const c=(typeof e.className==='string')?e.className:'';if(c)s+='.'+c.trim().split(/\s+/).slice(0,2).join('.');return s;}
const A=[],B=[],P=[];let cand=0;
for(const e of document.querySelectorAll(SEL)){if(e.tabIndex<0||e.disabled)continue;if(!e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}))continue;if(e.getBoundingClientRect().height<1)continue;cand++;if(document.activeElement&&document.activeElement!==document.body)document.activeElement.blur();const b=snap(e);e.focus({preventScroll:true});if(document.activeElement!==e){e.blur();continue;}const a2=snap(e),r=e.getBoundingClientRect(),ch=Object.keys(b).filter(x=>b[x]!==a2[x]);e.blur();if(!ch.length){A.push({sel:L(e),txt:(e.textContent||e.value||'').trim().slice(0,30)});continue;}if(!ch.every(x=>OUT.includes(x)))continue;const fw=parseFloat(a2['outline-width'])||0,fo=parseFloat(a2['outline-offset'])||0,st=a2['outline-style'];if(st==='none'||fw===0){A.push({sel:L(e),txt:'outline-style:none'});continue;}const c=cl(e);if(!c)continue;const cr=c.getBoundingClientRect(),need=fw+Math.max(fo,0),rm={ust:r.top-cr.top,alt:cr.bottom-r.bottom,sol:r.left-cr.left,sag:cr.right-r.right};const vis=Object.values(rm).filter(v=>v>=need-0.5).length;if(vis<=1)B.push({sel:L(e),kirpan:L(c),vis,txt:(e.textContent||'').trim().slice(0,26)});else if(vis<=2)P.push({sel:L(e),kirpan:L(c),vis});}
k.remove();const ag=o=>{const m={};for(const x of o){const q=x.sel+(x.kirpan?' < '+x.kirpan:'');m[q]=m[q]||{k:q,n:0,d:x};m[q].n++;}return Object.values(m).sort((p,q)=>q.n-p.n).slice(0,8);};
JSON.stringify({page:location.pathname,cand,A:A.length,Aagg:ag(A),B:B.length,Bagg:ag(B),P:P.length,Pagg:ag(P)})
})()
