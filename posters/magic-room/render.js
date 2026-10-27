const {chromium}=require('playwright');
(async()=>{const dir=process.argv[2];const b=await chromium.launch({args:['--allow-file-access-from-files']});
const pg=await b.newPage({viewport:{width:1080,height:1350},deviceScaleFactor:2});
const jobs=[['3clean.png','land&ar='+(2000/1127),'poster-3']];
for(const [img,m,out] of jobs){await pg.goto(`file://${dir}/poster.html?img=${img}&mode=${m}`);
await pg.evaluate(()=>document.fonts.ready);await pg.waitForTimeout(800);
await pg.screenshot({path:`${dir}/${out}.png`});}
await b.close();})();
