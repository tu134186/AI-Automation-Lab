const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const {validateReceipt,updateStatus,recordReceipt}=require('./record_receipt.cjs');
const sha='a'.repeat(40),snapshot='b'.repeat(40),digest='c'.repeat(64);
const value={verified:true,source_commit:sha,snapshot_commit:snapshot,run_id:'42',bytes:80000,sha256:digest,files:12};
const readme='# Overview\n<!-- DOWNLOAD_RECEIPT_START -->\n待验收\n<!-- DOWNLOAD_RECEIPT_END -->\nrest';
async function main() {
  const base=fs.mkdtempSync(path.join(os.tmpdir(),'receipt-test-'));
  const cwd=process.cwd(),oldEnv=process.env.VERIFIED_SNAPSHOT_SHA;
  try {
    assert.equal(validateReceipt(value,sha,snapshot,42),value);
    for(const changed of [{verified:false},{run_id:'99'},{sha256:'invalid'},{bytes:0},{snapshot_commit:'d'.repeat(40)}])
      assert.throws(()=>validateReceipt({...value,...changed},sha,snapshot,42));
    assert.match(updateStatus(readme),/回读：已通过/);
    assert.ok(updateStatus(readme).endsWith('rest'));
    assert.throws(()=>updateStatus('missing'));
    process.chdir(base);process.env.VERIFIED_SNAPSHOT_SHA=snapshot;
    fs.mkdirSync('downloaded-verification');
    fs.writeFileSync('downloaded-verification/download-verification.json',JSON.stringify(value));
    let stale=false,badHash=false,writes=[];
    const github={rest:{git:{
      getRef:async args=>({data:{object:{sha:args.ref.includes('feature/')?sha:(stale?'d'.repeat(40):snapshot)}}}),
      getCommit:async()=>({data:{tree:{sha:'base-tree'}}}),
      createBlob:async args=>{writes.push(['blob',args]);return {data:{sha:'blob'}};},
      createTree:async args=>{writes.push(['tree',args]);return {data:{sha:'tree'}};},
      createCommit:async args=>{writes.push(['commit',args]);return {data:{sha:'receipt'}};},
      updateRef:async args=>{writes.push(['ref',args]);return {};}
    },repos:{getContent:async args=>{
      const files={'snapshot.json':JSON.stringify({source_commit:sha,run_id:42}),
        'complete-delivery.zip.sha256':(badHash?'d'.repeat(64):digest)+'  complete-delivery.zip\n',
        'README.md':readme};
      const data=Buffer.from(files[args.path]);
      return {data:{type:'file',encoding:'base64',size:data.length,content:data.toString('base64')}};
    }}}};
    const summary={addHeading(){return this;},addLink(){return this;},async write(){}};
    const core={info(){},summary},context={repo:{owner:'tu134186',repo:'AI-Automation-Lab'},ref:'refs/heads/feature/report-center-20261029',sha,runId:42};
    await recordReceipt({github,context,core});
    const tree=writes.find(x=>x[0]==='tree')[1];
    assert.equal(tree.base_tree,'base-tree');
    assert.deepEqual(tree.tree.map(x=>x.path).sort(),['README.md','download-verification.json','download-verification.md']);
    assert.equal(writes.find(x=>x[0]==='ref')[1].ref,'heads/reports-latest');
    assert.equal(writes.find(x=>x[0]==='ref')[1].force,false);
    assert.deepEqual(writes.find(x=>x[0]==='commit')[1].parents,[snapshot]);
    writes=[];stale=true;
    await assert.rejects(()=>recordReceipt({github,context,core}),/Stale/);
    assert.equal(writes.length,0);
    stale=false;badHash=true;
    await assert.rejects(()=>recordReceipt({github,context,core}),/does not match/);
    assert.equal(writes.length,0);
    await assert.rejects(()=>recordReceipt({github,context:{...context,ref:'refs/heads/main'},core}),/Unauthorized/);
    console.log('Receipt validation, stale guard, hash binding and scoped writes: PASS');
  } finally {
    process.chdir(cwd);
    if(oldEnv===undefined) delete process.env.VERIFIED_SNAPSHOT_SHA;
    else process.env.VERIFIED_SNAPSHOT_SHA=oldEnv;
    fs.rmSync(base,{recursive:true,force:true});
  }
}
main().catch(e=>{console.error(e);process.exitCode=1;});

