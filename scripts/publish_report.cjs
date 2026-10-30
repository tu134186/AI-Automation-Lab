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

function validateBundle(folder, sha) {
  if (!/^[0-9a-f]{40}$/.test(sha)) throw new Error('Invalid bundle Commit');
  const name = 'AI-Automation-Lab-' + sha.slice(0,7) + '-complete.zip';
  const expected = [name,name+'.sha256'].sort();
  if (JSON.stringify(fs.readdirSync(folder).sort()) !== JSON.stringify(expected))
    throw new Error('Unexpected complete bundle file list');
  for (const filename of expected) {
    const stat = fs.lstatSync(path.join(folder,filename));
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 10*1024*1024)
      throw new Error('Invalid complete bundle file');
  }
  const data = fs.readFileSync(path.join(folder,name));
  const digest = crypto.createHash('sha256').update(data).digest('hex');
  const sums = fs.readFileSync(path.join(folder,name+'.sha256'),'utf8');
  if (!data.length || sums !== digest + '  ' + name + '\n') throw new Error('Complete bundle hash mismatch');
  return {'complete-delivery.zip':data,
          'complete-delivery.zip.sha256':Buffer.from(digest+'  complete-delivery.zip\n')};
}

function archiveEntry(snapshot, commit) {
  if (!/^[0-9a-f]{40}$/.test(commit) || !/^[0-9a-f]{40}$/.test(snapshot.source_commit)
      || !Number.isSafeInteger(snapshot.run_id) || snapshot.run_id < 1
      || !Number.isFinite(new Date(snapshot.updated_at).getTime()))
    throw new Error('Invalid delivery archive evidence');
  return {snapshot_commit:commit,source_commit:snapshot.source_commit,run_id:snapshot.run_id,
    updated_at:snapshot.updated_at,
    download_url:'https://github.com/tu134186/AI-Automation-Lab/raw/' + commit + '/complete-delivery.zip'};
}

function archiveList(previous, older) {
  const result = [];
  const seen = new Set();
  for (const item of [previous,...older].filter(Boolean)) {
    const entry = archiveEntry(item,item.snapshot_commit);
    if (!seen.has(entry.snapshot_commit)) {
      seen.add(entry.snapshot_commit);
      result.push(entry);
    }
    if (result.length === 5) break;
  }
  return result;
}

async function previousDeliveries(github,owner,repo,parent) {
  if (!parent) return [];
  async function readJson(filename, optional=false) {
    try {
      const response = await github.rest.repos.getContent({owner,repo,path:filename,ref:parent});
      const file = response.data;
      if (file.type !== 'file' || file.encoding !== 'base64' || file.size > 100000)
        throw new Error('Invalid previous delivery metadata');
      return JSON.parse(Buffer.from(file.content,'base64').toString('utf8'));
    } catch (error) {
      if (optional && error.status === 404) return null;
      throw error;
    }
  }
  const [snapshot,history] = await Promise.all([
    readJson('snapshot.json'),readJson('delivery_history.json',true)]);
  if (history && (history.schema !== 1 || !Array.isArray(history.previous) || history.previous.length > 5))
    throw new Error('Invalid prior delivery index');
  let previous = null;
  try {
    const bundle = await github.rest.repos.getContent({owner,repo,path:'complete-delivery.zip',ref:parent});
    if (bundle.data.type !== 'file' || bundle.data.size <= 0 || bundle.data.size > 10*1024*1024)
      throw new Error('Invalid previous complete ZIP');
    previous = archiveEntry(snapshot,parent);
  } catch (error) {
    if (error.status !== 404) throw error;
  }
  return archiveList(previous,history ? history.previous : []);
}

function md(value) {
  return String(value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/[\\\`*_\[\]|]/g, c => '&#' + c.charCodeAt(0) + ';').replace(/[\r\n]+/g,' ');
}

function renderOverview(report, history, diagnosis, snapshot, deliveries=[]) {
  if (report.context?.commit !== snapshot.source_commit || report.all_passed !== true
      || !Number.isSafeInteger(report.total) || report.total < 1
      || !Number.isSafeInteger(history.scanned_count) || history.scanned_count < 0
      || !Array.isArray(diagnosis.items) || !/^[0-9a-f]{40}$/.test(snapshot.source_commit)
      || !Number.isSafeInteger(snapshot.run_id) || snapshot.run_id < 1)
    throw new Error('Invalid overview evidence');
  const date = new Date(snapshot.updated_at);
  if (!Number.isFinite(date.getTime())) throw new Error('Invalid snapshot date');
  const local = new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',
    day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(date);
  const repo = 'https://github.com/tu134186/AI-Automation-Lab';
  const current = repo + '/actions?query=branch%3Afeature%2Freport-center-20261029';
  const badge = repo + '/actions/workflows/lab-check.yml/badge.svg?branch=feature%2Freport-center-20261029';
  const source = 'AI-Automation-Lab-' + snapshot.source_commit.slice(0,7) + '-source.zip';
  const paused = diagnosis.paused || [];
  if (!Array.isArray(paused)) throw new Error('Invalid paused evidence');
  const lines = ['# 报告中心 · 手机总览','',
    '## 已保存的核验快照','',
    '| 项目 | 结果 |','| --- | --- |',
    '| 本次自动检查 | 全部通过，共 ' + report.total + ' 项 |',
    '| 历史待处理 | ' + diagnosis.items.length + ' 项，独立于本次检查结果 |',
    '| 已暂停实验 | ' + paused.length + ' 项，保留原结论，不计为修复 |',
    '| 历史扫描 | ' + history.scanned_count + ' 次 |',
    '| 快照更新时间 | ' + local + '（北京时间） |','',
    '源码 Commit：' + snapshot.source_commit,'',
    '[本快照对应任务](' + repo + '/actions/runs/' + snapshot.run_id + ') · [核验说明](delivery.md)','',
    '## 当前任务状态','',
    '[![GitHub 当前工作流状态](' + badge + ')](' + current + ')','',
    '[查看当前任务列表](' + current + ')。上方快照只在核验成功后更新；新任务运行中或失败时，这里可能仍是上次成功结果。徽章由 GitHub 加载，可能有缓存，以任务页为准。','',
    '## 需要关注',''];
  if (!diagnosis.items.length) lines.push('本次扫描未发现待处理；不代表未扫描的旧任务全部正常。');
  for (const item of diagnosis.items.slice(0,5)) {
    const label = md((String(item.name || '未命名任务')).slice(0,100));
    lines.push('- **' + md(item.kind || '待核对') + '：' + label + '**（' + md(item.branch || '') + '）');
    lines.push('  ' + md(item.direction || '请查看诊断清单中的证据。'));
    if (Number.isSafeInteger(item.id) && item.id > 0)
      lines.push('  [查看证据任务](' + repo + '/actions/runs/' + item.id + ')');
  }
  if (diagnosis.items.length > 5) lines.push('其余事项请查看完整待处理清单。');
  lines.push('','## 已暂停实验','');
  if (!paused.length) lines.push('本次扫描没有匹配的暂停实验。');
  for (const item of paused.slice(0,5)) {
    lines.push('- **' + md(String(item.name || '实验').slice(0,100)) + '**：' + md(item.pause_reason || '原因见诊断清单。'));
    lines.push('  原始结果：' + md(item.original_conclusion || '未知') + '，暂停不代表通过或已修复。');
    if (Number.isSafeInteger(item.id) && item.id > 0)
      lines.push('  [原任务证据](' + repo + '/actions/runs/' + item.id + ')');
  }
  lines.push('','## 历史交付包','',
    '下面的链接锁定报告归档 Commit，后续更新最新入口不会改变这些链接对应的旧包。','');
  if (!deliveries.length) lines.push('尚无已记录的历史完整包。');
  for (const candidate of deliveries) {
    const item = archiveEntry(candidate,candidate.snapshot_commit);
    const time = new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',
      day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(item.updated_at));
    lines.push('- [源码 ' + item.source_commit.slice(0,7) + ' · ' + time + '（北京时间）](' + item.download_url + ')');
  }
  lines.push('','## 查看与下载','',
    '- [下载完整交付包：报告、诊断、日志、校验清单和源码](complete-delivery.zip)',
    '- [完整包 SHA-256](complete-delivery.zip.sha256)',
    '- [完整中文报告](report.md)',
    '- [待处理清单](diagnosis.md)',
    '- [历史任务与产物入口](history.md)',
    '- [下载对应源码 ZIP](' + source + ')',
    '- [文件校验清单](SHA256SUMS.txt)','',
    '本分支保存快照，不受 Actions 产物保留期限制；删除仓库、分支或文件后仍会丢失。主分支未因报告发布而修改。','',
    '完整 ZIP 有独立 SHA-256；包内清单校验原始交付文件。本分支额外的总览与来源说明不在包内清单范围。','');
  return lines.join('\n');
}

async function publish({github, context, core}) {
  const {owner, repo} = context.repo;
  const sourceBranch = 'feature/report-center-20261029';
  const target = 'reports-latest';
  if (owner !== 'tu134186' || repo !== 'AI-Automation-Lab'
      || context.ref !== 'refs/heads/' + sourceBranch) throw new Error('Unauthorized snapshot target');
  const files = validateSnapshot('downloaded-report', context.sha, context.runId);
  Object.assign(files, validateBundle('downloaded-bundle', context.sha));
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
  const deliveryHistory = {schema:1,current_source_commit:context.sha,current_run_id:context.runId,
    previous:await previousDeliveries(github,owner,repo,parent)};
  files['delivery_history.json'] = Buffer.from(JSON.stringify(deliveryHistory,null,2)+'\n');
  files['snapshot.json'] = Buffer.from(JSON.stringify(snapshot,null,2) + '\n');
  files['README.md'] = Buffer.from(renderOverview(
    JSON.parse(files['report.json'].toString('utf8')),
    JSON.parse(files['history.json'].toString('utf8')),
    JSON.parse(files['diagnosis.json'].toString('utf8')), snapshot, deliveryHistory.previous));
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
  const url = 'https://github.com/' + owner + '/' + repo + '/blob/' + target + '/README.md';
  core.info('Published verified snapshot: ' + commit.data.sha);
  await core.summary.addHeading('固定报告入口已更新').addLink('查看最新中文报告',url)
    .addRaw('\n').addLink('本次交付包（锁定归档 Commit）',
      'https://github.com/' + owner + '/' + repo + '/raw/' + commit.data.sha + '/complete-delivery.zip')
    .addRaw('\n源码 Commit：' + context.sha + '\n').write();
}
module.exports = {validateSnapshot,validateBundle,publish,renderOverview,archiveEntry,archiveList};

