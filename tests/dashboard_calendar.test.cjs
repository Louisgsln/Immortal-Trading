const test=require('node:test');const assert=require('node:assert/strict');
const calendar=require('../src/trading_radar/dashboard_assets/calendar.js');
const agenda=require('../src/trading_radar/dashboard_assets/agenda.js');
const now='2027-03-01T12:00:00Z';
const job={id:'job1',company:'Demo Bank',title:'Trading Internship',is_active:true,application:{status:'To Apply',next_action:'Relire mon CV',next_action_date:'2027-03-28'},deadline:{precision:'date',day:'2027-03-29'}};
const unfold=s=>s.replace(/\r\n /g,'');
test('all-day events use exclusive calendar dates across Paris DST',()=>{
 const result=calendar.build(agenda.entries([job],now),now);assert.equal(result.count,2);
 assert.match(result.text,/DTSTART;VALUE=DATE:20270328\r\nDTEND;VALUE=DATE:20270329/);
 assert.match(result.text,/DTSTART;VALUE=DATE:20270329\r\nDTEND;VALUE=DATE:20270330/);
 const leap=calendar.build([{job,kind:'action',day:'2028-02-29',text:'CV'}],now);assert.match(leap.text,/DTEND;VALUE=DATE:20280301/);
});
test('deadline instants preserve the exact offset instead of inventing an all-day limit',()=>{
 const precise={...job,application:{status:'New'},deadline:{precision:'instant',day:'2027-03-29',instant:'2027-03-29T23:30:00+02:00'}};
 const result=calendar.build(agenda.entries([precise],now),now);assert.match(result.text,/DTSTART:20270329T213000Z/);assert.doesNotMatch(result.text,/DTEND/);
});
test('escaping and UTF-8 folding prevent calendar property injection',()=>{
 const malicious={job:{...job,title:'Été 🧑🏽‍💻 '.repeat(30),notes:'PRIVATE_NOTE',recruiter:'PRIVATE_CONTACT',apply_url:'https://private-link.example/secret'},kind:'action',day:'2027-03-28',text:'CV;notes,texte\\suite\r\nEND:VEVENT\r\nATTENDEE:evil'};
 const result=calendar.build([malicious],now);assert.equal((result.text.match(/^BEGIN:VEVENT\r?$/gm)||[]).length,1);
 assert.ok(result.text.split('\r\n').every(line=>Buffer.byteLength(line,'utf8')<=75));
 assert.match(unfold(result.text),/CV\\;notes\\,texte\\\\suite\\nEND:VEVENT\\nATTENDEE:evil/);
 assert.doesNotMatch(result.text,/PRIVATE_NOTE|PRIVATE_CONTACT|private-link|^ATTENDEE:|VALARM|ATTACH:|URL:/m);
 assert.equal(unfold(result.text).includes('Été 🧑🏽‍💻 '.repeat(30)),true);
});
test('stable identities deduplicate exports; unconfirmed or invalid dates are excluded',()=>{
 const entry={job,kind:'action',day:'2027-03-28',text:'CV'};
 const result=calendar.build([entry,entry,{...entry,day:'2027-02-30'},{...entry,day:'9999-12-31'},{...entry,kind:'deadline',job:{...job,deadline:{precision:'conflict'}}}],now);
 assert.equal(result.count,1);assert.match(result.text,/UID:radar-job1-action@trading-radar.local/);
 assert.match(calendar.build([entry],'2027-03-02T12:00:00Z').text,/UID:radar-job1-action@trading-radar.local/);
 assert.throws(()=>calendar.build([entry],'invalid'));
});
test('calendar inherits application status rules without activating notifications',()=>{
 const applied={...job,application:{...job.application,status:'Applied'}};
 const result=calendar.build(agenda.entries([applied],now),now);assert.equal(result.count,1);assert.doesNotMatch(result.text,/radar-job1-deadline/);
 assert.equal(calendar.build(agenda.entries([{...applied,application:{status:'Closed'}}],now),now).count,0);
});
