/* K-P  CANLI RENDER KONTRASTI  v2  (CPO, 21.09.2026) — KAPI DEGIL, canli denetci
 *
 * NEDEN AYRI BIR OLCUM
 * --------------------
 * tools/contrast-check.py (K-I) kendi basliginda kapsam sinirini yaziyor:
 *   "YALNIZCA ikisi de AYNI yerde yazili ciftleri gorur (80 cift). MIRAS
 *    alinan zemin uzerindeki metni (SAYFADAKI COGU METIN) goremez, cunku
 *    zemini statik olarak bilemez. Yari saydam degerler de ATLANIR."
 * Bu betik tam o kor noktayi olcer: gercek render'da her gorunur metin
 * dugumunun computed rengi + GERCEKTEN BOYANMIS zemin zinciri, yari saydam
 * katmanlar sirayla birlestirilerek.
 *
 * 21.09 ilk kosumun bulgusu: `color:var(--bp-sat)` duz zeminde 5.49:1 ile
 * rahat gecerken, ayni kural `background:rgba(var(--bp-sat-rgb),.12+)` de
 * veriyorsa metnin ARKASI kirmizilasiyor ve oran 4.27'ye dusuyordu (/ozet'te
 * 53 kart). K-I bunu goremez: renkler ayni kuralda YAZILI ama biri yari
 * saydam, yani gercek karisim ancak render'da bellidir.
 *
 * KULLANIM
 * --------
 * Browser pane konsolunda calistir; JSON ozet doner. CSP 'unsafe-eval'
 * icermedigi icin new Function()/eval() SAYFA ICINDE calismaz — betigi
 * sayfalar arasi tasimak icin <script> enjeksiyonu kullan ('unsafe-inline'
 * izinli):
 *   const s=document.createElement('script');
 *   s.textContent='window.__KP='+localStorage.getItem('__kp');
 *   document.head.appendChild(s); window.__KP();
 *
 * ALFA=0 METIN UC SINIFA AYRILIR (v1 ucunu de ihlal saniyordu)
 * ------------------------------------------------------------
 *   GRADIENT  background-clip:text + gradient -> duraklarin EN KOTUSU olculur
 *   STROKE    -webkit-text-stroke  -> kontur rengi olculur
 *   GORUNMEZ  ne gradyan ne kontur -> gercek bug, ayri listede raporlanir
 * Ayrica `-webkit-text-fill-color` `color`u ezer; v2 once onu okur.
 *
 * POZITIF KONTROL SART (ilk denemem BASARISIZ oldu, iki nedenle birden)
 * ---------------------------------------------------------------------
 *  1. Yeni eklenen <style> AYNI TICK'TE uygulanmaz -> rAF x2 bekle (K-O).
 *  2. Zehir icin secilen sinif GERCEKTEN taranan bir oge olmali: masaustunde
 *     `.bp-nav-item` rect'i 0x0 (mobil nav), dedektor onu zaten eliyordu.
 * Dogru yol: dedektorun FIILEN taradigi ogelere hem opak hem YARI SAYDAM
 * dusuk kontrast enjekte et, yakalandigini gor, geri al, taban degismedi mi
 * kontrol et.
 *
 * BILINEN KOR NOKTALAR (bkz. feedback_kural_da_kanitlanmali)
 * ----------------------------------------------------------
 *  * Atada background-image/gradient varsa gercek zemin bilinemez -> ihlal
 *    sayilmaz, AMBIG listesinde raporlanir.
 *  * Metnin UZERINDE duran absolute/overlay katmanlar hesaba katilmaz.
 *  * :hover/:focus gibi durum renkleri ancak durum TETIKLENIRSE olculur.
 */
(() => {
  const cA=(a)=>(isFinite(a)?Math.min(1,Math.max(0,a)):1);
  function parse(c){ if(!c) return null; const m=c.match(/rgba?\(([^)]+)\)/); if(!m) return null;
    const p=m[1].split(/[,\s/]+/).filter(Boolean).map(Number); if(p.length<3||p.some(n=>!isFinite(n))) return null;
    return {r:p[0],g:p[1],b:p[2],a:p.length>3?cA(p[3]):1}; }
  const over=(s,d)=>({r:s.r*s.a+d.r*(1-s.a),g:s.g*s.a+d.g*(1-s.a),b:s.b*s.a+d.b*(1-s.a),a:1});
  function lum(c){const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);};return .2126*f(c.r)+.7152*f(c.g)+.0722*f(c.b);}
  const ratio=(a,b)=>{const l1=lum(a),l2=lum(b);return (Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);};
  function sig(el){let s=el.tagName.toLowerCase(); if(el.id)s+='#'+el.id;
    const cl=(el.getAttribute('class')||'').trim().split(/\s+/).filter(Boolean); if(cl.length)s+='.'+cl.slice(0,4).join('.'); return s;}
  const SR=(cs)=>{const cp=cs.clipPath||'',cl=cs.clip||'';return (cp.includes('inset(50%')||cl.includes('rect(0')||cl.includes('rect(1px'))&&parseFloat(cs.width)<=2;};
  const stops=(bi)=>{const o=[];const re=/rgba?\([^)]+\)/g;let m;while((m=re.exec(bi))){const c=parse(m[0]);if(c&&c.a>0)o.push(c);}return o;};
  const V=[],AMB=[],INV=[]; let scanned=0,textNodes=0; const skipped={};
  const bump=k=>skipped[k]=(skipped[k]||0)+1;
  for(const el of document.querySelectorAll('*')){
    let txt=''; for(const n of el.childNodes) if(n.nodeType===3) txt+=n.nodeValue;
    txt=txt.replace(/\s+/g,' ').trim(); if(!txt) continue; textNodes++;
    const cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden'){bump('gizli');continue;}
    const rc=el.getBoundingClientRect(); if(rc.width<1||rc.height<1){bump('sifir-kutu');continue;}
    if(SR(cs)){bump('sr-only');continue;}
    if(el.closest('[aria-hidden="true"]')){bump('aria-hidden');continue;}
    let opac=1,p=el; while(p&&p!==document.documentElement){opac*=parseFloat(getComputedStyle(p).opacity||'1');p=p.parentElement;}
    if(opac<0.15){bump('opaklik');continue;}
    /* ZEMIN ZINCIRI: ilk OPAK atada dur, ustteki yari saydam katmanlari uzerine yaz */
    const L=[]; let ambSrc=null,node=el;
    while(node){ const s=getComputedStyle(node); const bi=s.backgroundImage;
      const selfTextGrad = node===el && (s.webkitBackgroundClip==='text'||s.backgroundClip==='text');
      if(bi&&bi!=='none'&&!selfTextGrad&&!ambSrc) ambSrc=sig(node)+' :: '+bi.slice(0,50);
      const bc=parse(s.backgroundColor);
      if(bc&&bc.a>0){L.push(bc); if(bc.a>=.999) break;}
      node=node.parentElement; }
    let bg = L.length&&L[L.length-1].a>=.999 ? L.pop() : (parse(getComputedStyle(document.documentElement).backgroundColor)||{r:255,g:255,b:255,a:1});
    if(bg.a<.999) bg=over(bg,{r:255,g:255,b:255,a:1});
    for(let i=L.length-1;i>=0;i--) bg=over(L[i],bg);
    /* ETKIN METIN RENGI: -webkit-text-fill-color, color'u ezer */
    const tf=parse(cs.webkitTextFillColor), co=parse(cs.color);
    let fg0 = tf || co; if(!fg0){bump('renk');continue;}
    const isTextGrad=(cs.webkitBackgroundClip==='text'||cs.backgroundClip==='text')&&cs.backgroundImage!=='none';
    const sw=parseFloat(cs.webkitTextStrokeWidth)||0, sc=parse(cs.webkitTextStrokeColor);
    const fsz=parseFloat(cs.fontSize)||16, fw=parseInt(cs.fontWeight,10)||400;
    const need=(fsz>=24||(fsz>=18.66&&fw>=700))?3.0:4.5;   /* WCAG 2.1 AA buyuk metin 3:1 */
    let kind='PLAIN', cr, fgLabel=cs.color;
    scanned++;
    if(fg0.a<0.999){
      if(isTextGrad){ kind='GRADIENT'; const st=stops(cs.backgroundImage);
        if(!st.length){bump('gradyan-durak-yok');continue;}
        cr=Math.min(...st.map(s=>ratio(s.a<.999?over(s,bg):s,bg)));
        fgLabel='grad['+st.map(s=>`${Math.round(s.r)},${Math.round(s.g)},${Math.round(s.b)}`).join(' | ')+']'; }
      else if(sw>0&&sc&&sc.a>0){ kind='STROKE'; cr=ratio(sc.a<.999?over(sc,bg):sc,bg);
        fgLabel='stroke '+cs.webkitTextStrokeColor+' @'+cs.webkitTextStrokeWidth; }
      else if(fg0.a<=0.02){ INV.push({sig:sig(el),text:txt.slice(0,40),fg:cs.color,tf:cs.webkitTextFillColor,
        bgImage:cs.backgroundImage.slice(0,40),px:+fsz.toFixed(1)}); continue; }
      else { kind='ALPHA'; cr=ratio(over(fg0,bg),bg); }
    } else cr=ratio(fg0,bg);
    if(cr+0.005<need){
      const rec={sig:sig(el),kind,text:txt.slice(0,44),ratio:+cr.toFixed(2),need,fg:fgLabel,
        bg:`rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})`,px:+fsz.toFixed(1),w:fw};
      if(ambSrc){rec.bgImage=ambSrc; AMB.push(rec);} else V.push(rec);
    }
  }
  const grp=a=>{const m=new Map();for(const v of a){const k=v.sig+'|'+v.ratio;if(!m.has(k))m.set(k,{...v,count:0});m.get(k).count++;}
    return [...m.values()].sort((x,y)=>x.ratio-y.ratio);};
  return {url:location.pathname,scanned,textNodes,skipped,HARD:grp(V),AMBIG:grp(AMB),INVISIBLE:INV,
    hardCount:V.length,ambigCount:AMB.length,invCount:INV.length};
})()
