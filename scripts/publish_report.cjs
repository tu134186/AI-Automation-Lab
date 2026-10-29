const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

function validateSnapshot(folder, sha, runId) {
  if (!/^[0-9a-f]{40}$/.test(sha)) throw new Error('Invalid source Commit');
  const required = ['report.json','report.md','report.html','tests.log','history.json','history.md',
    'diagnosis.json','diagnosis.md','delivery.md', 'AI-Automation-Lab-' + sha.slice(0,7) + '-source.zip'];
  const expected = [...required, 'manifest.json', 'SHA256SUMS.txt'].sort();
  const found = fs.readdirSync(folder).sort();
  if (JSON.stringify(found) !== JSON.stringify(expected)) throw new Error('Unexpected delivery file list');
  const buffers = {};
  let total = 0;
  for (const name of expected) {
    const filename = path.join(folder, name);
    const stat = fs.lstatSync(filename);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 5*1024*1024)
      throw new Error('Invalid delivery file');
    const data = fs.readFileSync(filename);
    total += data.length;
    buffers[name] = data;
  }
  if (total > 20*1024*1024) throw new Error('Delivery exceeds size limit');
  const manifest = JSON.parse(buffers['manifest.json'].toString('utf8'));
  if (manifest.schema !== 1 || manifest.commit !== sha || manifest.run_id !== String(runId)
      || manifest.test_state !== '全部通过') throw new Error('Delivery identity or test result mismatch');
  if (JSON.stringify(Object.keys(manifest.files).sort()) !== JSON.stringify(required.sort()))
    throw new Error('Manifest file list mismatch');
  for (const [name, entry] of Object.entries(manifest.files)) {
    const data = buffers[name];
    const digest = crypto.createHash('sha256').update(data).digest('hex');
    if (entry.bytes !== data.length || entry.sha256 !== digest) throw new Error('SHA-256 mismatch: ' + name);
  }
  const sums = Object.entries(manifest.files).map(([name, item]) => item.sha256 + '  ' + name + '\n').join('');
  if (buffers['SHA256SUMS.txt'].toString('utf8') !== sums) throw new Error('Checksum list mismatch');
  return buffers;
}

async function publish({github, context, core}) {
  const {owner, repo} = context.repo;
  const sourceBranch = 'feature/report-center-20261029';
  const target = 'reports-latest';
  if (owner !== 'tu134186' || repo !== 'AI-Automation-Lab'
      || context.ref !== 'refs/heads/' + sourceBranch) throw new Error('Unauthorized snapshot target');
  const files = validateSnapshot('downloaded-report', context.sha, context.runId);
  const source = await github.rest.git.getRef({owner, repo, ref:'heads/' + sourceBranch});
  if (source.data.object.sha !== context.sha) throw new Error('Source branch changed; refuse stale publication');
  let parent = null;
  try {
    const previous = await github.rest.git.getRef({owner, repo, ref:'heads/' + target});
    parent = previous.data.object.sha;
  } catch (error) {
    if (error.status !== 404) throw error;
  }
  const snapshot = {schema:1,source_commit:context.sha,run_id:context.runId,
    run_url:'https://github.com/' + owner + '/' + repo + '/actions/runs/' + context.runId,
    updated_at:new Date().toISOString()};
  files['snapshot.json'] = Buffer.from(JSON.stringify(snapshot,null,2) + '\n');
  files['README.md'] = Buffer.from('# 最新已核验报告\n\n'
    + '[直接查看中文报告](report.md) · [待处理清单](diagnosis.md) · [历史任务](history.md)\n\n'
    + '源码 Commit：' + context.sha + '\n\n'
    + '[本次云端任务](' + snapshot.run_url + ')\n\n'
    + '[下载对应源码 ZIP](AI-Automation-Lab-' + context.sha.slice(0,7) + '-source.zip)\n\n'
    + '本分支由云端保存最新已核验快照；不依赖 Actions 产物保留天数，直到分支或文件被删除。\n'
    + '数据是采集时快照，不是实时状态。最新报告任务若失败，本分支保留上次成功快照，请以 Commit 和任务链接核对时间。\n'
    + '交付校验文件覆盖下载包中的原始 10 个文件，不包含本分支额外生成的 README.md 和 snapshot.json。\n');
  const entries = await Promise.all(Object.entries(files).map(async ([filename,data]) => {
    const blob = await github.rest.git.createBlob({owner,repo,encoding:'base64',content:data.toString('base64')});
    return {path:filename,mode:'100644',type:'blob',sha:blob.data.sha};
  }));
  const tree = await github.rest.git.createTree({owner,repo,tree:entries});
  const commit = await github.rest.git.createCommit({owner,repo,tree:tree.data.sha,
    parents:parent ? [parent] : [], message:'reports: verified snapshot for ' + context.sha.slice(0,7)});
  if (parent) {
    await github.rest.git.updateRef({owner,repo,ref:'heads/' + target,sha:commit.data.sha,force:false});
  } else {
    await github.rest.git.createRef({owner,repo,ref:'refs/heads/' + target,sha:commit.data.sha});
  }
  const url = 'https://github.com/' + owner + '/' + repo + '/blob/' + target + '/report.md';
  core.info('Published verified snapshot: ' + commit.data.sha);
  await core.summary.addHeading('固定报告入口已更新').addLink('查看最新中文报告',url)
    .addRaw('\n源码 Commit：' + context.sha + '\n').write();
}
module.exports = {validateSnapshot,publish};

