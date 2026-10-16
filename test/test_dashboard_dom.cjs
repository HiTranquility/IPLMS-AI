// Offline regression: execute the actual inline script against a tiny DOM.
// Run: node test/test_dashboard_dom.cjs (no packages or browser downloads).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../static/index.html'), 'utf8');
assert(!/\b(?:innerHTML|outerHTML|insertAdjacentHTML|document\.write)\b/.test(html));
assert(!/(?:src|href)=["']https?:/i.test(html));
const elements = new Map();
function node() { return {textContent:'', children:[], value:'', addEventListener(){}, replaceChildren(){this.children=[];}, append(child){this.children.push(child);}}; }
const document = {getElementById(id){ if(!elements.has(id))elements.set(id,node());return elements.get(id);},createElement:node};
const context = vm.createContext({document, crypto:{randomUUID:()=> 'synthetic-id'}, JSON});
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
vm.runInContext(script, context);
const attack = '<img src=x onerror="globalThis.pwned=true"><script>pwned=true</script>';
context.query = attack;
context.result = {data:[{answer:attack,sources:[attack]}]};
vm.runInContext('renderAnswer(query,result)', context);
assert.equal(elements.get('answer').textContent, 'Câu hỏi: '+attack+'\n\n'+attack);
assert.equal(elements.get('sources').children[1].textContent, attack);
context.attack = attack;
vm.runInContext("display('system-result',{server:attack}); display('ingest-result',attack)",context);
assert(elements.get('system-result').textContent.includes(attack.replaceAll('"','\\"')));
assert.equal(elements.get('ingest-result').textContent,attack);
assert.equal(context.pwned,undefined);
console.log('Dashboard hostile query/answer/source/system/error payloads remain text; no external assets.');
