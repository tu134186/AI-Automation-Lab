const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {validateSnapshot,publish} = require('./publish_report.cjs');
const sha = 'a'.repeat(40);
const base = fs.mkdtempSync(path.join(os.tmpdir(),'report-publish-'));
const original = process.cwd();
function fixture() {
  const folder = path.join(base,'downloaded-report');
  fs.rmSync(folder,{recursive:true,force:true});
  fs.mkdirSync(folder);
  const names = ['report.json','report.md','report.html','tests.log','history.json','history.md',
    'diagnosis.json','diagnosis.md','delivery.md','AI-Automation-Lab-'+sha.slice(0,7)+'-source.zip'].sort();
  const files = {};
  for (const name of names) {
    const data = Buffer.from('fixture '+name);
    fs.writeFileSync(path.join(folder,name),data);
    files[name]={bytes:data.length,sha256:crypto.createHash('sha256').update(data).digest('hex')};
  }
  fs.writeFileSync(path.join(folder,'manifest.json'),JSON.stringify({schema:1,commit:sha,run_id:'123',test_state:'全部通过',files}));
  fs.writeFileSync(path.join(folder,'SHA256SUMS.txt'),Object.entries(files).map(([name,x])=>x.sha256+'  '+name+'\n').join(''));
  return folder;
}
async function main() {
  try {
    process.chdir(base);
    let folder=fixture();
    assert.equal(Object.keys(validateSnapshot(folder,sha,123)).length,12);
    assert.throws(()=>validateSnapshot(folder,sha,456));
    assert.throws(()=>validateSnapshot(folder,'b'.repeat(40),123));
    fs.appendFileSync(path.join(folder,'report.md'),'corrupt');
    assert.throws(()=>validateSnapshot(folder,sha,123),/SHA-256/);
    folder=fixture();
    fs.writeFileSync(path.join(folder,'extra.txt'),'extra');
    assert.throws(()=>validateSnapshot(folder,sha,123),/file list/);
    folder=fixture();
    fs.unlinkSync(path.join(folder,'report.md'));
    fs.symlinkSync(path.join(folder,'tests.log'),path.join(folder,'report.md'));
    assert.throws(()=>validateSnapshot(folder,sha,123),/Invalid delivery file/);
    fixture();
    const context={repo:{owner:'tu134186',repo:'AI-Automation-Lab'},ref:'refs/heads/feature/report-center-20261029',sha,runId:123};
    let writes=[];
    let stale=false;
    let existing=false;
    const github={rest:{git:{
      getRef:async args=>{
        if(args.ref==='heads/feature/report-center-20261029')
          return {data:{object:{sha:stale?'b'.repeat(40):sha}}};
        if(existing) return {data:{object:{sha:'previous'}}};
        throw Object.assign(new Error('not found'),{status:404});
      },
      createBlob:async args=>{writes.push(['blob',args]);return {data:{sha:'blob'}};},
      createTree:async args=>{writes.push(['tree',args]);return {data:{sha:'tree'}};},
      createCommit:async args=>{writes.push(['commit',args]);return {data:{sha:'snapshot'}};},
      createRef:async args=>{writes.push(['ref',args]);return {};},
      updateRef:async args=>{writes.push(['update',args]);return {};}
    }}};
    const summary={addHeading(){return this;},addLink(){return this;},addRaw(){return this;},async write(){}};
    const core={info(){},summary};
    await publish({github,context,core});
    assert.equal(writes.find(x=>x[0]==='ref')[1].ref,'refs/heads/reports-latest');
    assert.equal(writes.find(x=>x[0]==='tree')[1].tree.length,14);
    writes=[];existing=true;
    await publish({github,context,core});
    assert.equal(writes.find(x=>x[0]==='update')[1].ref,'heads/reports-latest');
    assert.equal(writes.find(x=>x[0]==='update')[1].force,false);
    assert.deepEqual(writes.find(x=>x[0]==='commit')[1].parents,['previous']);
    writes=[];stale=true;
    await assert.rejects(()=>publish({github,context,core}),/Source branch changed/);
    assert.equal(writes.length,0);
    await assert.rejects(()=>publish({github,context:{...context,ref:'refs/heads/main'},core}),/Unauthorized/);
    assert.equal(writes.length,0);
    console.log('Snapshot validation, tamper, symlink, scope and stale-source checks: PASS');
  } finally {
    process.chdir(original);
    fs.rmSync(base,{recursive:true,force:true});
  }
}
main().catch(error=>{console.error(error);process.exitCode=1;});

