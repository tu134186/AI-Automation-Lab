const fs = require('node:fs');

const START = '<!-- DOWNLOAD_RECEIPT_START -->';
const END = '<!-- DOWNLOAD_RECEIPT_END -->';
function validateReceipt(value, sha, snapshot, runId) {
  if (!value || value.verified !== true || value.source_commit !== sha
      || value.snapshot_commit !== snapshot || value.run_id !== String(runId)
      || !/^[0-9a-f]{40}$/.test(sha) || !/^[0-9a-f]{40}$/.test(snapshot)
      || !/^[0-9a-f]{64}$/.test(value.sha256) || value.files !== 12
      || !Number.isSafeInteger(value.bytes) || value.bytes <= 0 || value.bytes > 10*1024*1024)
    throw new Error('Invalid download verification receipt');
  return value;
}
function updateStatus(readme) {
  if (readme.split(START).length !== 2 || readme.split(END).length !== 2)
    throw new Error('Missing or repeated receipt status block');
  const begin = readme.indexOf(START), end = readme.indexOf(END);
  if (end < begin) throw new Error('Invalid receipt status order');
  return readme.slice(0,begin) + START + '\n**发布后下载回读：已通过**\n\n'
    + '[查看独立下载验收凭据](download-verification.md)\n' + END + readme.slice(end+END.length);
}
async function recordReceipt({github,context,core}) {
  const {owner,repo}=context.repo;
  if (owner!=='tu134186' || repo!=='AI-Automation-Lab'
      || context.ref!=='refs/heads/feature/report-center-20261029')
    throw new Error('Unauthorized receipt publication');
  const snapshot = process.env.VERIFIED_SNAPSHOT_SHA;
  const filename='downloaded-verification/download-verification.json';
  const stat=fs.lstatSync(filename);
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size>10000)
    throw new Error('Invalid receipt file');
  const value=validateReceipt(JSON.parse(fs.readFileSync(filename,'utf8')),context.sha,snapshot,context.runId);
  const source=await github.rest.git.getRef({owner,repo,ref:'heads/feature/report-center-20261029'});
  const current=await github.rest.git.getRef({owner,repo,ref:'heads/reports-latest'});
  if (source.data.object.sha!==context.sha || current.data.object.sha!==snapshot)
    throw new Error('Stale source or snapshot; refuse receipt update');
  async function read(name) {
    const response=await github.rest.repos.getContent({owner,repo,path:name,ref:snapshot});
    const file=response.data;
    if (file.type!=='file' || file.encoding!=='base64' || file.size>100000)
      throw new Error('Invalid snapshot metadata');
    return Buffer.from(file.content,'base64').toString('utf8');
  }
  const [metadata,checksum,readme]=await Promise.all([read('snapshot.json'),read('complete-delivery.zip.sha256'),read('README.md')]);
  const identity=JSON.parse(metadata);
  if (identity.source_commit!==context.sha || String(identity.run_id)!==String(context.runId)
      || checksum!==value.sha256+'  complete-delivery.zip\n')
    throw new Error('Receipt does not match published package');
  const receipt={...value,recorded_at:new Date().toISOString()};
  const recordedLocal=new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',
    day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(receipt.recorded_at));
  const markdown='# 独立下载回读验收：PASS\n\n'
    + '- 源码 Commit：'+value.source_commit+'\n'
    + '- 已回读的归档 Commit：'+value.snapshot_commit+'\n'
    + '- Run ID：'+value.run_id+'\n'
    + '- 实际下载字节数：'+value.bytes+'\n'
    + '- SHA-256：'+value.sha256+'\n'
    + '- 包内文件：12，报告、诊断、源码及清单一致性通过。\n'
    + '- 凭据登记时间（北京时间）：'+recordedLocal+'\n\n'
    + '[下载已验收的锁定包](https://github.com/'+owner+'/'+repo+'/raw/'+snapshot+'/complete-delivery.zip)\n\n'
    + '独立只读任务从 GitHub 取回实际内容并复核。本凭据不表示用户手机网络也已测试。\n';
  const files={'download-verification.json':JSON.stringify(receipt,null,2)+'\n',
               'download-verification.md':markdown,'README.md':updateStatus(readme)};
  const base=await github.rest.git.getCommit({owner,repo,commit_sha:snapshot});
  const treeEntries=await Promise.all(Object.entries(files).map(async([path,content])=>{
    const blob=await github.rest.git.createBlob({owner,repo,encoding:'utf-8',content});
    return {path,mode:'100644',type:'blob',sha:blob.data.sha};
  }));
  const tree=await github.rest.git.createTree({owner,repo,base_tree:base.data.tree.sha,tree:treeEntries});
  const commit=await github.rest.git.createCommit({owner,repo,parents:[snapshot],tree:tree.data.sha,
    message:'reports: persist independent download receipt for '+context.sha.slice(0,7)});
  await github.rest.git.updateRef({owner,repo,ref:'heads/reports-latest',sha:commit.data.sha,force:false});
  core.info('Download receipt persisted: '+commit.data.sha);
  await core.summary.addHeading('下载验收凭据已保存')
    .addLink('查看持久验收凭据','https://github.com/'+owner+'/'+repo+'/blob/'+commit.data.sha+'/download-verification.md').write();
}
module.exports={validateReceipt,updateStatus,recordReceipt};

