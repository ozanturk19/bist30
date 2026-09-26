/* K-Z  DURUM KONTRASTI (WCAG 1.4.11 — :hover / :active)  v1  (CPO, 21.09.2026)
 *      KAPI DEGIL — canli denetci.
 *
 * NEDEN AYRI BIR OLCUM
 * --------------------
 * K-Q (tools/nontext-contrast-check.js) kendi basliginda KOR NOKTASINI yaziyor:
 *   "* :hover/:focus/:active durum renkleri tetiklenmedikce olculmez."
 * K-Y (58f5cf4 + 0b65cc7) dolgusuz kontrollerin REST sinirlarini 3:1 uzerine
 * cikardi (--bp-ctl-border) ama :hover kurallari ayrica taranmadi. Bu betik
 * o bosluğu olcer. Bkz. [[reference_statik_kapinin_itiraf_ettigi_bosluk...]].
 *
 * SORU
 * ----
 * Bir kontrolun TEK kimligi kutusuysa (ikon-only / bos form alani), FARE
 * UZERINE GELINCE o kimlik zayiflasiyor mu? Hover affordansi GUCLENDIRMELI;
 * tersi calisan bir hover, K-W'nin "iskelet TERS yonde akiyordu" bulgusunun
 * kardesidir.
 *
 * YONTEM — NEDEN CSSOM DEGIL, GERCEK BILDIRIM UYGULAMASI
 * -------------------------------------------------------
 * K-X dersi: "bu sinif tanimli mi" STATIK olarak cevaplanamaz, tek zemin
 * gercegi canli CSSOM (`document.styleSheets`) — JS string'inden enjekte
 * edilen stiller de oradadir (static/bp-search.js, static/learning-mode.js
 * hover kurallarini oradan enjekte ediyor).
 * Ama CSSOM'dan okunan ham deger `var(--bp-border2)` / `1px solid X` gibi
 * COZULMEMIS olur. Bu yuzden eslesen hover bildirimlerini ogenin KENDISINE
 * gecici olarak satir-ici uygulayip computed stili okuyoruz: var(), kisayol
 * ve adlandirilmis renkleri tarayicinin kendisi cozer. Olcum bitince
 * satir-ici stil AYNEN geri alinir (taban dogrulamasi sonda yapilir).
 *
 * BILINEN KOR NOKTALAR (durust liste)
 * -----------------------------------
 *   * OZGULLUK (specificity) yok sayilir: eslesen tum :hover kurallari kaynak
 *     sirasiyla birlestirilir. Gercekte daha ozgul bir kural kazanabilir ->
 *     bu yuzden POZITIF KONTROL sart: bulgularin en az ikisi GERCEK fare
 *     hover'i ile (CDP Input.dispatchMouseEvent / computer hover) dogrulanmali.
 *   * ATA hover'i olculmez: kontrolun DIS ZEMINI de hover'da degisiyorsa
 *     (kart hover'i) hesaba katilmaz.
 *   * :focus / :focus-visible bu betigin kapsaminda DEGIL — o eksen K-O'da
 *     ayrica olculdu (odak halkasi), ve `:focus-visible` SON GIRIS MODUNA
 *     bagli oldugu icin ayri bir kosum ister.
 *   * Gecis (transition) sureleri: computed stil ANINDA okunur, hover
 *     kurallari satir-ici uygulandigi icin transition ara degeri OKUNABILIR.
 *     Bu yuzden olcumden once `transition-duration:0s` enjekte edilir
 *     (K-O dersi: "transition :focus olcumunu bayatlatir").
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

  function bgOf(start){
    const L=[]; let node=start;
    while(node){ const s=getComputedStyle(node); const bc=parse(s.backgroundColor);
      if(bc&&bc.a>0){ L.push(bc); if(bc.a>=.999) break; }
      node=node.parentElement; }
    let bg = L.length&&L[L.length-1].a>=.999 ? L.pop()
           : (parse(getComputedStyle(document.documentElement).backgroundColor)||{r:255,g:255,b:255,a:1});
    if(bg.a<.999) bg=over(bg,{r:255,g:255,b:255,a:1});
    for(let i=L.length-1;i>=0;i--) bg=over(L[i],bg);
    return bg;
  }

  const SEL='a[href],button,input:not([type=hidden]),select,textarea,summary,'+
            '[role=button],[role=link],[role=checkbox],[role=switch],[role=tab],'+
            '[role=radio],[role=menuitem],[role=option],[tabindex]:not([tabindex="-1"])';
  const NEED=3.0;
  const FORMT=new Set(['text','email','search','number','tel','url','password','date','month','week','time','datetime-local']);
  /* olculen durum bildirimleri — sadece TANINABILIRLIGI etkileyenler */
  const PROPS=['background','background-color','border','border-color','border-top','border-right',
    'border-bottom','border-left','border-top-color','border-right-color','border-bottom-color',
    'border-left-color','border-width','border-top-width','border-right-width','border-bottom-width',
    'border-left-width','border-style','outline','outline-color','outline-width','outline-style','box-shadow','opacity'];

  /* ---- 1) CSSOM'dan durum kurallarini hasat et ---- */
  const STATES=['hover','active'];
  const harvest={hover:[],active:[]};   /* {base, decl, order, spec} */
  const plain=[];                       /* durumsuz kurallar: {base, order, spec} */
  /* (a,b,c) ozgullugu -> tek sayi. Yeterli hassasiyet: id<<16 | sinif<<8 | tip */
  function spec(sel){
    let a=0,b=0,c=0; const t=sel.replace(/\[[^\]]*\]/g,m=>{b++;return ' ';});
    a=(t.match(/#[\w-]+/g)||[]).length;
    b+=(t.match(/\.[\w-]+/g)||[]).length;
    b+=(t.match(/:(?!:)[a-z-]+/g)||[]).filter(x=>!/^:(not|is|where)$/.test(x)).length;
    c=(t.match(/(^|[\s>+~])[a-z][\w-]*/gi)||[]).length;
    return (a<<16)|(b<<8)|c;
  }
  let sheetsRead=0, sheetsBlocked=0, rulesSeen=0, mediaSkipped=0, order=0;
  function walk(rules){
    for(const r of rules){
      /* TUZAK (canli olculdu): Chrome'da CSSStyleRule ARTIK cssRules tasir
         (ic ice CSS destegi) -> `if(r.cssRules)` ile ayirmak HER kurali
         gruplayici sanip yutar. Ilk kosumda rulesSeen=0 verdi. Ayirt edici
         olan `r.style`in VARLIGI. */
      if(r.cssRules && r.cssRules.length && !r.style){
        /* @media/@supports kosulu O AN eslesmiyorsa icindeki durum kurallari
           UYGULANMAZ; harmanlamak yanlis viewport'un hover'ini raporlar. */
        if(r.conditionText!==undefined){ let mm=true;
          try{mm=window.matchMedia(r.conditionText).matches;}catch(e){}
          if(!mm){ mediaSkipped++; continue; } }
        try{walk(r.cssRules);}catch(e){} continue;
      }
      if(r.cssRules && r.cssRules.length && r.style){ try{walk(r.cssRules);}catch(e){} }
      if(!r.selectorText||!r.style) continue;
      rulesSeen++; order++;
      /* DURUMSUZ kurallar da toplanir: bir durum kurali ancak kendisinden
         SONRA gelen ve EN AZ ayni ozgullukteki bir durumsuz kural yoksa
         kazanir. (Canli kanit: .mbn-sheet-item:active CSSOM 27, ardindan
         .mbn-sheet-item.active 28 -> ESIT ozgullukte, SONRAKI kazanir;
         yesil sinir aslinda HIC kaybolmuyor.) */
      if(!r.selectorText.includes(':hover')&&!r.selectorText.includes(':active')){
        for(const part of r.selectorText.split(',')){
          const p=part.trim(); if(!p) continue;
          let bd=''; for(const prop of PROPS){ const v=r.style.getPropertyValue(prop); if(v) bd=prop; }
          if(bd) plain.push({base:p,order,spec:spec(p)});
        }
      }
      for(const st of STATES){
        if(!r.selectorText.includes(':'+st)) continue;
        for(const part of r.selectorText.split(',')){
          const p=part.trim(); if(!p.includes(':'+st)) continue;
          /* :hover'i kaldir -> taban secici. Sonda olmayan :hover'lar (ata hover)
             da kalkar; bu ELEMENT hover'i DEGILDIR -> sonda olani sart kos. */
          if(!/:hover(\s*)$/.test(p)&&st==='hover') continue;
          if(!/:active(\s*)$/.test(p)&&st==='active') continue;
          const base=p.replace(new RegExp(':'+st+'\\s*$'),'').trim();
          if(!base) continue;
          let decl='';
          for(const prop of PROPS){ const v=r.style.getPropertyValue(prop); if(v) decl+=prop+':'+v+' !important;'; }
          if(!decl) continue;
          harvest[st].push({base,decl,order,spec:spec(p)});
        }
      }
    }
  }
  for(const sh of document.styleSheets){
    try{ const rr=sh.cssRules; if(!rr){sheetsBlocked++;continue;} sheetsRead++; walk(rr); }
    catch(e){ sheetsBlocked++; }
  }

  /* ---- 2) transition'i sifirla (K-O dersi) ---- */
  const kill=document.createElement('style');
  kill.textContent='*,*::before,*::after{transition-duration:0s!important;animation-duration:0s!important}';
  document.head.appendChild(kill);
  void document.body.offsetHeight;

  /* ---- 3) skor fonksiyonu (K-Q ile ayni taninabilirlik tanimi) ---- */
  function score(el,ob){
    const cs=getComputedStyle(el);
    const own=parse(cs.backgroundColor);
    const inner=(own&&own.a>0)?over(own,ob):ob;
    const bgR=(own&&own.a>0.02)?ratio(inner,ob):0;
    let bdR=0,bdLabel='';
    for(const side of ['Top','Right','Bottom','Left']){
      const w=parseFloat(cs['border'+side+'Width'])||0, st=cs['border'+side+'Style'];
      if(w<0.5||st==='none'||st==='hidden') continue;
      const bc=parse(cs['border'+side+'Color']); if(!bc||bc.a<=0.02) continue;
      const eff=bc.a<.999?over(bc,inner):bc; const r=ratio(eff,ob);
      if(r>bdR){bdR=r;bdLabel=cs['border'+side+'Color']+' @'+w.toFixed(1)+'px';}
    }
    const ow=parseFloat(cs.outlineWidth)||0;
    if(ow>=0.5&&cs.outlineStyle!=='none'){ const oc=parse(cs.outlineColor);
      if(oc&&oc.a>0.02){ const r=ratio(oc.a<.999?over(oc,ob):oc,ob); if(r>bdR){bdR=r;bdLabel='outline '+cs.outlineColor;} } }
    let shR=0; const bs=cs.boxShadow||'none';
    if(bs!=='none'){ const re=/rgba?\([^)]+\)/g; let m;
      while((m=re.exec(bs))){ const c=parse(m[0]); if(!c||c.a<=0.02) continue;
        const r=ratio(c.a<.999?over(c,ob):c,ob); if(r>shR) shR=r; } }
    /* ikon boyasi (metinsiz kontrolde tanitici) */
    let icoR=0;
    for(const q of el.querySelectorAll('svg,svg path,svg circle,svg rect,svg line,svg polyline,svg polygon,svg ellipse')){
      const qs=getComputedStyle(q);
      for(const prop of ['fill','stroke']){
        const raw=qs[prop]; if(!raw||raw==='none'||raw.includes('url(')) continue;
        if(prop==='stroke'&&(parseFloat(qs.strokeWidth)||0)<=0) continue;
        const c=parse(raw); if(!c||c.a<=0.02) continue;
        const opv=parseFloat(qs[prop==='fill'?'fillOpacity':'strokeOpacity']||'1');
        const eff={...c,a:cA(c.a*(isFinite(opv)?opv:1))}; if(eff.a<=0.02) continue;
        const r=ratio(eff.a<.999?over(eff,inner):eff,inner); if(r>icoR) icoR=r;
      }
    }
    { const w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT); let n;
      while((n=w.nextNode())){ if(!n.nodeValue||!n.nodeValue.trim()) continue;
        const pe=n.parentElement; if(!pe) continue; const ps=getComputedStyle(pe);
        if(ps.display==='none'||ps.visibility==='hidden'||SR(ps)) continue;
        const c=parse(ps.color); if(!c||c.a<=0.02) continue;
        const r=ratio(c.a<.999?over(c,inner):c,inner); if(r>icoR) icoR=r; } }
    return {s:Math.max(bgR,bdR,shR,icoR),bgR,bdR,shR,icoR,bdLabel,
      fill:(own&&own.a>0.02)?cs.backgroundColor:'-'};
  }

  /* ---- 4) tara ---- */
  const V=[],DROP=[]; let scanned=0,stateful=0; const skipped={};
  const bump=k=>skipped[k]=(skipped[k]||0)+1;
  for(const el of document.querySelectorAll(SEL)){
    const cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden'){bump('gizli');continue;}
    const rc=el.getBoundingClientRect(); if(rc.width<2||rc.height<2){bump('sifir-kutu');continue;}
    if(SR(cs)){bump('sr-only');continue;}
    if(el.closest('[aria-hidden="true"]')){bump('aria-hidden');continue;}
    if(el.disabled||el.getAttribute('aria-disabled')==='true'){bump('devre-disi');continue;}
    const tag=el.tagName.toLowerCase();
    const itype=(el.getAttribute('type')||'text').toLowerCase();
    if(tag==='input'&&(itype==='checkbox'||itype==='radio')){bump('native-kutu');continue;}
    const isForm=(tag==='input'&&FORMT.has(itype))||tag==='textarea'||tag==='select';
    let vis='';
    { const w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT); let n;
      while((n=w.nextNode())){ if(!n.nodeValue||!n.nodeValue.trim()) continue;
        let ok=true,a=n.parentElement;
        while(a&&a!==el.parentElement){ const as=getComputedStyle(a);
          if(as.display==='none'||as.visibility==='hidden'||SR(as)||a.getAttribute('aria-hidden')==='true'){ok=false;break;}
          a=a.parentElement; }
        if(ok) vis+=n.nodeValue; } }
    vis=vis.replace(/\s+/g,' ').trim();
    /* KAPSAM = K-Y ile AYNI: FORM (deger bos olabilir) + IKONSUZ (gorunur metni yok).
       METINLI kontroller K-Q muafiyeti altinda — kendi metniyle taninir. */
    /* K-Y kapsami HARD icin gecerli (FORM + IKONSUZ). METINLI kontroller
       WCAG'ca muaf ama DURUM GERILEMESI tasarim bilgisi olarak olculur. */
    const isMetinli=(!isForm&&vis.length>0); if(isMetinli) bump('METINLI-olculdu');
    scanned++;

    const ob=bgOf(el.parentElement||document.body);
    const base=score(el,ob);

    for(const st of STATES){
      let decl='', best=null;
      for(const h of harvest[st]){ let ok=false; try{ok=el.matches(h.base);}catch(e){}
        if(!ok) continue; decl+=h.decl;
        if(!best||h.spec>best.spec||(h.spec===best.spec&&h.order>best.order)) best=h; }
      if(!decl) continue;
      /* KASKAT KAPISI: durum kuralini EZEN bir durumsuz kural var mi?
         (sonra gelen + en az ayni ozgullukte) -> varsa durum HIC uygulanmaz. */
      let overridden=false;
      for(const q of plain){ let ok=false; try{ok=el.matches(q.base);}catch(e){}
        if(!ok) continue;
        if(q.spec>best.spec||(q.spec===best.spec&&q.order>best.order)){ overridden=true; break; } }
      if(overridden){ bump('durum-kurali-EZILMIS'); continue; }
      stateful++;
      const saved=el.getAttribute('style');
      el.style.cssText=(saved||'')+';'+decl;
      void el.offsetHeight;
      const st2=score(el,ob);
      if(saved===null) el.removeAttribute('style'); else el.setAttribute('style',saved);
      void el.offsetHeight;
      const rec={sig:sig(el),state:st,text:vis.slice(0,32),
        klass:isForm?'FORM':'IKONSUZ',
        klassFinal:isMetinli?'METINLI':(isForm?'FORM':'IKONSUZ'),
        rest:+base.s.toFixed(2), stateScore:+st2.s.toFixed(2), need:NEED,
        restBdR:+base.bdR.toFixed(2), stateBdR:+st2.bdR.toFixed(2),
        restBorder:base.bdLabel||'-', stateBorder:st2.bdLabel||'-',
        restFill:base.fill, stateFill:st2.fill,
        outside:`rgb(${Math.round(ob.r)}, ${Math.round(ob.g)}, ${Math.round(ob.b)})`,
        box:Math.round(rc.width)+'x'+Math.round(rc.height)};
      rec.klass=rec.klassFinal;
      if(!isMetinli && st2.s+0.005<NEED) V.push(rec);       /* IHLAL: durumda 3:1 alti */
      else if(base.bdR>=NEED && st2.bdR+0.05<base.bdR) DROP.push(rec);
      /* DROP = "rest'i 3:1 USTUNDE olan bir sinir, durumda ASAGI cekiliyor".
         Kartlarin hover'i (rest ~1.3 -> 1.97) YUKARI gider, bu kapiya takilmaz. */
    }
  }

  /* ---- 5) tabanin bozulmadigini kanitla (K-S dersi: olcum sirasi katmani bozar) ---- */
  kill.remove();
  void document.body.offsetHeight;
  let dirty=0;
  for(const el of document.querySelectorAll(SEL)){
    const s=el.getAttribute('style')||'';
    if(s.includes('!important')&&PROPS.some(p=>s.includes(p+':'))) dirty++;
  }

  const grp=a=>{const m=new Map();for(const v of a){const k=v.sig+'|'+v.state+'|'+v.stateScore;
      if(!m.has(k))m.set(k,{...v,count:0});m.get(k).count++;}
    return [...m.values()].sort((x,y)=>x.stateScore-y.stateScore);};
  return {url:location.pathname,vw:window.innerWidth,
    sheetsRead,sheetsBlocked,rulesSeen,mediaSkipped,plainRules:plain.length,
    harvested:{hover:harvest.hover.length,active:harvest.active.length},
    scanned,stateful,skipped,dirtyAfter:dirty,
    HARD:grp(V),REGRESS:grp(DROP),hardCount:V.length,regressCount:DROP.length};
})()
