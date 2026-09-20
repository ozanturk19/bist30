/* K-Q  METIN-DISI KONTRAST (WCAG 1.4.11, 3:1)  v1  (CPO, 21.09.2026)
 *      KAPI DEGIL — canli denetci.
 *
 * NEDEN AYRI BIR OLCUM
 * --------------------
 * K-I (tools/contrast-check.py) ve K-P (tools/live-contrast-check.js) yalniz
 * METIN olcer (WCAG 1.4.3). K-P turunun kendi dersinde yazili:
 *   "kenarlik ayri bir WCAG ekseni (1.4.11, 3:1); metin tokenini oraya
 *    sizdirmak iki ekseni birbirine baglar."
 * Bu eksen bugune kadar HIC olculmedi. 1.4.11 iki seyi ister:
 *   (a) UI BILESENI  — kontrolu TANIMAK icin gereken gorsel (kenarlik/dolgu)
 *   (b) GRAFIK NESNE — icerigi anlamak icin gereken grafik (anlam tasiyan ikon)
 * her ikisi de KOMSU renge karsi >= 3:1.
 *
 * YANLIS POZITIFTEN KACINMA — KAPSAM DARALTMASI (v1 ilk kosumun dersi)
 * ---------------------------------------------------------------------
 * Ilk surum "gorsel siniri olan her kontrol" olcuyordu ve /ozet'te 220 isabet
 * verdi — bunlarin 159'u `.stock-card`, yani ICINDE kod/ad/fiyat METNI olan
 * kartlardi. WCAG 1.4.11 Understanding: sinir ancak bileseni TANIMAK icin
 * GEREKLIYSE 3:1 ister; kontrolu kendi gorunur metni tanitiyorsa sinir
 * "gerekli gorsel bilgi" DEGILDIR (o metin zaten 1.4.3 kapsaminda). Bu yuzden
 * kapsam UCE ayrildi ve ihlal yalniz ilk ikisinde sayilir:
 *
 *   FORM      input(metin turleri)/textarea/select — degeri BOS olabilir,
 *             alani bulmanin TEK yolu sinirdir. 1.4.11'in kanonik ornegi.
 *   IKONSUZ   gorunur metni olmayan kontrol (ikon butonu) — onu ya sinir ya
 *             da ikonun kendisi tanitir; ikisinden biri >= 3:1 olmali.
 *   METINLI   gorunur metni olan diger kontroller -> MUAF, sayilir (textIdent)
 *             ama ihlal degil. Zayif sinirlari ZAYIF-SINIR listesine yazilir
 *             (tasarim bilgisi, WCAG bulgusu degil).
 *
 * TANINABILIRLIK SKORU (FORM ve IKONSUZ icin)
 *     skor = max( zemin-vs-disZemin , kenarlik-vs-disZemin , golge-vs-disZemin ,
 *                 IKONSUZ ise ikonun en iyi boyasi-vs-zemin )
 * skor >= 3 ise GECER.
 *
 * ANLAM TASIYAN IKON
 * ------------------
 * Her <svg> degil: yalniz (a) metinsiz bir kontrolun TEK icerigi olan, ya da
 * (b) role="img"/aria-label tasiyan SVG'ler. Bunlarda fill/stroke renkleri
 * zemine karsi olculur. aria-hidden ve suslu (decorative) olanlar elenir.
 *
 * MUAFIYETLER (WCAG metnine gore)
 * -------------------------------
 *   * disabled / aria-disabled kontroller ("inactive component") ATLANIR.
 *   * gizli, sifir kutulu, sr-only, aria-hidden altindakiler ATLANIR.
 *   * Kart/ayrac gibi SUSLU kenarliklar kapsam disi — bu betik YALNIZ
 *     etkilesimli kontrollere bakar, dekoratif kutulara degil.
 *
 * BILINEN KOR NOKTALAR
 * --------------------
 *   * :hover/:focus/:active durum renkleri tetiklenmedikce olculmez (K-G'nin
 *     durum-kurali dersi bu eksende de gecerli).
 *   * background-image/gradient zeminli atalarda gercek zemin bilinemez ->
 *     AMBIG listesine dusulur, ihlal sayilmaz.
 *   * SECILI/SECILI-DEGIL gibi DURUM AYRIMI (1.4.11 "states") olculmez;
 *     yalniz bilesenin kendisinin taninabilirligi olculur.
 *   * Kontrolun uzerinde duran overlay katmanlar hesaba katilmaz.
 *   * NATIVE checkbox/radio kutusunu TARAYICI boyar (`accent-color`); computed
 *     stil kutu kenarligini vermez -> OLCULEMEZ olarak raporlanir, ihlal
 *     sayilmaz. (K-K bu yuzeyleri ayrica elden gecirmisti.)
 *
 * POZITIF KONTROL SART: dedektorun FIILEN taradigi bir kontrole dusuk
 * kontrastli kenarlik enjekte et (yeni <style> ayni tick'te uygulanmaz,
 * rAF x2 bekle), yakalandigini gor, geri al, taban degismedi mi bak.
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

  /* DIS ZEMIN: ogenin ATASINDAN baslayarak ilk opak zemine kadar birlestir */
  function bgOf(start){
    const L=[]; let amb=null,node=start;
    while(node){ const s=getComputedStyle(node); const bi=s.backgroundImage;
      if(bi&&bi!=='none'&&!amb) amb=sig(node)+' :: '+bi.slice(0,46);
      const bc=parse(s.backgroundColor);
      if(bc&&bc.a>0){ L.push(bc); if(bc.a>=.999) break; }
      node=node.parentElement; }
    let bg = L.length&&L[L.length-1].a>=.999 ? L.pop()
           : (parse(getComputedStyle(document.documentElement).backgroundColor)||{r:255,g:255,b:255,a:1});
    if(bg.a<.999) bg=over(bg,{r:255,g:255,b:255,a:1});
    for(let i=L.length-1;i>=0;i--) bg=over(L[i],bg);
    return {bg,amb};
  }

  const SEL='a[href],button,input:not([type=hidden]),select,textarea,summary,'+
            '[role=button],[role=link],[role=checkbox],[role=switch],[role=tab],'+
            '[role=radio],[role=menuitem],[role=option],[tabindex]:not([tabindex="-1"])';
  const NEED=3.0;
  const V=[],AMB=[],ICON=[],WEAK=[],UNMEAS=[]; let scanned=0,textIdent=0,iconScanned=0; const skipped={};
  const FORMT=new Set(['text','email','search','number','tel','url','password','date','month','week','time','datetime-local']);
  /* ikonu olan metinsiz kontrolde ikonun EN IYI boyasi da bir tanitici sayilir */
  function iconScore(el,ob){
    let best=0, urlPaint=false;
    for(const q of el.querySelectorAll('svg,svg path,svg circle,svg rect,svg line,svg polyline,svg polygon,svg ellipse')){
      const qs=getComputedStyle(q);
      for(const prop of ['fill','stroke']){
        const raw=qs[prop]; if(!raw||raw==='none') continue;
        if(prop==='stroke'&&(parseFloat(qs.strokeWidth)||0)<=0) continue;
        if(raw.includes('url(')){urlPaint=true;continue;}   /* gradyan/pattern boya OLCULEMEZ */
        const c=parse(raw); if(!c||c.a<=0.02) continue;
        const opv=parseFloat(qs[prop==='fill'?'fillOpacity':'strokeOpacity']||'1');
        const eff={...c,a:cA(c.a*(isFinite(opv)?opv:1))}; if(eff.a<=0.02) continue;
        const r=ratio(eff.a<.999?over(eff,ob):eff,ob); if(r>best) best=r;
      }
    }
    /* ARIA-HIDDEN METIN GLIFI de bir ikondur (ornek: <span aria-hidden>⏸</span>).
       v1 bunu goremiyordu: gorunur-metin hesabi aria-hidden'i ELER, iconScore ise
       yalniz SVG'ye bakiyordu -> #macroPauseBtn skor 0 ile SAHTE POZITIF verdi. */
    { const w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT); let n;
      while((n=w.nextNode())){ if(!n.nodeValue||!n.nodeValue.trim()) continue;
        const pe=n.parentElement; if(!pe) continue; const ps=getComputedStyle(pe);
        if(ps.display==='none'||ps.visibility==='hidden'||SR(ps)) continue;
        const c=parse(ps.color); if(!c||c.a<=0.02) continue;
        const r=ratio(c.a<.999?over(c,ob):c,ob); if(r>best) best=r; } }
    /* metin olmayan gorsel isaret ::before/::after ile de gelebilir (ok, hamburger) */
    for(const pe of ['::before','::after']){
      const ps=getComputedStyle(el,pe); if(!ps||ps.content==='none'||ps.content==='normal') continue;
      const pc=parse(ps.color); const pb=parse(ps.backgroundColor); const pw=parseFloat(ps.width)||0;
      if(ps.content!=='""'&&pc&&pc.a>0.02){ const r=ratio(pc.a<.999?over(pc,ob):pc,ob); if(r>best) best=r; }
      if(pb&&pb.a>0.02&&pw>=1){ const r=ratio(over(pb,ob),ob); if(r>best) best=r; }
      const pbw=parseFloat(ps.borderTopWidth)||0, pbc=parse(ps.borderTopColor);
      if(pbw>=0.5&&pbc&&pbc.a>0.02){ const r=ratio(pbc.a<.999?over(pbc,ob):pbc,ob); if(r>best) best=r; }
    }
    return {best,urlPaint};
  }
  const bump=k=>skipped[k]=(skipped[k]||0)+1;

  const ctrls=new Set(document.querySelectorAll(SEL));
  for(const el of ctrls){
    const cs=getComputedStyle(el);
    if(cs.display==='none'||cs.visibility==='hidden'){bump('gizli');continue;}
    const rc=el.getBoundingClientRect(); if(rc.width<2||rc.height<2){bump('sifir-kutu');continue;}
    if(SR(cs)){bump('sr-only');continue;}
    if(el.closest('[aria-hidden="true"]')){bump('aria-hidden');continue;}
    if(el.disabled||el.getAttribute('aria-disabled')==='true'){bump('devre-disi');continue;}
    let opac=1,p=el; while(p&&p!==document.documentElement){opac*=parseFloat(getComputedStyle(p).opacity||'1');p=p.parentElement;}
    if(opac<0.15){bump('opaklik');continue;}

    const outer=bgOf(el.parentElement||document.body);
    const ob=outer.bg;

    /* ic zemin (border-box: kendi zemini kenarligin ALTINA da boyanir) */
    const own=parse(cs.backgroundColor);
    const inner = (own&&own.a>0) ? over(own,ob) : ob;
    const hasFill = !!(own&&own.a>0.02);
    const bgR = hasFill ? ratio(inner,ob) : 0;

    /* kenarlik: her kenari ayri oku, gorunur olanlarin EN IYISINI al */
    let bdR=0, hasBorder=false, bdLabel='';
    for(const side of ['Top','Right','Bottom','Left']){
      const w=parseFloat(cs['border'+side+'Width'])||0;
      const st=cs['border'+side+'Style'];
      if(w<0.5||st==='none'||st==='hidden') continue;
      const bc=parse(cs['border'+side+'Color']); if(!bc||bc.a<=0.02) continue;
      hasBorder=true;
      const eff=bc.a<.999?over(bc,inner):bc;      /* yari saydam kenarlik kendi zemini uzerinde */
      const r=ratio(eff,ob);
      if(r>bdR){bdR=r;bdLabel=side.toLowerCase()+' '+cs['border'+side+'Color']+' @'+w.toFixed(1)+'px';}
    }
    /* outline de sinir olabilir (focus DEGIL, kalici outline) */
    const ow=parseFloat(cs.outlineWidth)||0, ost=cs.outlineStyle;
    if(ow>=0.5&&ost!=='none'){ const oc=parse(cs.outlineColor);
      if(oc&&oc.a>0.02){ hasBorder=true; const r=ratio(oc.a<.999?over(oc,ob):oc,ob);
        if(r>bdR){bdR=r;bdLabel='outline '+cs.outlineColor+' @'+ow.toFixed(1)+'px';} } }

    /* box-shadow sinir olarak kullanilabilir (ring deseni) */
    let shR=0, hasShadow=false;
    const bs=cs.boxShadow||'none';
    if(bs!=='none'){ const re=/rgba?\([^)]+\)/g; let m;
      while((m=re.exec(bs))){ const c=parse(m[0]); if(!c||c.a<=0.02) continue; hasShadow=true;
        const r=ratio(c.a<.999?over(c,ob):c,ob); if(r>shR) shR=r; } }

    scanned++;
    /* --- KAPSAM SINIFI --- */
    const tag=el.tagName.toLowerCase();
    const itype=(el.getAttribute('type')||'text').toLowerCase();
    const isNativeBox = tag==='input' && (itype==='checkbox'||itype==='radio');
    const isForm = (tag==='input'&&FORMT.has(itype)) || tag==='textarea' || tag==='select';
    /* GORUNUR metin: sr-only / gizli / aria-hidden alt agaclar HARIC.
       (aria-hidden ikon metni — "▾", "×" — tanitici METIN sayilmaz, ikondur.) */
    let vis='';
    { const w=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);
      let n; while((n=w.nextNode())){
        if(!n.nodeValue||!n.nodeValue.trim()) continue;
        let ok=true,a=n.parentElement;
        while(a&&a!==el.parentElement){ const as=getComputedStyle(a);
          if(as.display==='none'||as.visibility==='hidden'||SR(as)||a.getAttribute('aria-hidden')==='true'){ok=false;break;}
          a=a.parentElement; }
        if(ok) vis+=n.nodeValue; } }
    vis=vis.replace(/\s+/g,' ').trim();
    const hasText = vis.length>0;

    if(isNativeBox){ UNMEAS.push({sig:sig(el),type:itype,reason:'native accent-color kutusu computed stilde yok'}); continue; }

    const ic = hasText?{best:0,urlPaint:false}:iconScore(el,ob);
    const icoR = ic.best;
    /* Ogenin KENDI background-image'i bir affordans olabilir (ornek: .da-select
       oku bir data-URI SVG'dir). Rengini computed stilden okuyamayiz -> OLCULEMEZ. */
    const ownBgImg = cs.backgroundImage && cs.backgroundImage!=='none';
    const score=Math.max(bgR,bdR,shR,icoR);
    const rec={sig:sig(el), text:vis.slice(0,38),
      score:+score.toFixed(2), need:NEED,
      bgR:+bgR.toFixed(2), bdR:+bdR.toFixed(2), shR:+shR.toFixed(2), icoR:+icoR.toFixed(2),
      border:bdLabel||'-', fill:hasFill?cs.backgroundColor:'-',
      outside:`rgb(${Math.round(ob.r)}, ${Math.round(ob.g)}, ${Math.round(ob.b)})`,
      box:Math.round(rc.width)+'x'+Math.round(rc.height),
      klass:isForm?'FORM':(hasText?'METINLI':'IKONSUZ')};
    if(isForm||!hasText){
      if(score+0.005>=NEED) continue;                                  /* GECER */
      if(outer.amb){rec.bgImage=outer.amb; AMB.push(rec);} else V.push(rec);
    } else {
      textIdent++;
      if((hasFill||hasBorder||hasShadow)&&score+0.005<NEED) WEAK.push(rec);  /* bilgi, ihlal DEGIL */
    }
  }

  /* ---- ANLAM TASIYAN IKONLAR ---- */
  for(const svg of document.querySelectorAll('svg')){
    if(svg.closest('[aria-hidden="true"]')||svg.getAttribute('aria-hidden')==='true') continue;
    const host=svg.closest(SEL);
    const labelled=svg.getAttribute('role')==='img'||svg.hasAttribute('aria-label')||!!svg.querySelector('title');
    const soleContent = host && !(host.textContent||'').replace(/\s+/g,' ').trim();
    if(!labelled&&!soleContent) continue;                /* suslu ikon -> kapsam disi */
    const cs=getComputedStyle(svg);
    if(cs.display==='none'||cs.visibility==='hidden') continue;
    const rc=svg.getBoundingClientRect(); if(rc.width<2||rc.height<2) continue;
    const ob=bgOf(svg.parentElement||document.body).bg;
    iconScanned++;
    /* svg icindeki boyali her parca: fill veya stroke */
    let best=0,worst=Infinity,worstLabel='';
    const parts=[svg,...svg.querySelectorAll('path,circle,rect,line,polyline,polygon,ellipse')];
    for(const q of parts){
      const qs=getComputedStyle(q);
      for(const prop of ['fill','stroke']){
        const raw=qs[prop]; if(!raw||raw==='none') continue;
        if(prop==='stroke'&&(parseFloat(qs.strokeWidth)||0)<=0) continue;
        const c=parse(raw); if(!c||c.a<=0.02) continue;
        const opv=parseFloat(qs[prop==='fill'?'fillOpacity':'strokeOpacity']||'1');
        const eff={...c,a:cA(c.a*(isFinite(opv)?opv:1))};
        if(eff.a<=0.02) continue;
        const r=ratio(eff.a<.999?over(eff,ob):eff,ob);
        if(r>best) best=r;
        if(r<worst){worst=r;worstLabel=prop+' '+raw+(opv<1?' @'+opv:'');}
      }
    }
    if(!isFinite(worst)) continue;
    if(best+0.005<NEED) ICON.push({sig:sig(host||svg), text:(host?(host.getAttribute('aria-label')||''):'')||svg.getAttribute('aria-label')||'',
      best:+best.toFixed(2), worst:+worst.toFixed(2), paint:worstLabel,
      outside:`rgb(${Math.round(ob.r)}, ${Math.round(ob.g)}, ${Math.round(ob.b)})`,
      box:Math.round(rc.width)+'x'+Math.round(rc.height)});
  }

  const grp=a=>{const m=new Map();for(const v of a){const k=v.sig+'|'+(v.score!==undefined?v.score:v.best);
      if(!m.has(k))m.set(k,{...v,count:0});m.get(k).count++;}
    return [...m.values()].sort((x,y)=>(x.score!==undefined?x.score:x.best)-(y.score!==undefined?y.score:y.best));};
  return {url:location.pathname,scanned,textIdent,iconScanned,skipped,
    HARD:grp(V),AMBIG:grp(AMB),ICONS:grp(ICON),WEAK:grp(WEAK).slice(0,6),UNMEAS:UNMEAS.length,
    hardCount:V.length,ambigCount:AMB.length,iconCount:ICON.length,weakCount:WEAK.length};
})()
