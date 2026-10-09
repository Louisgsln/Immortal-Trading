const test = require('node:test');
const assert = require('node:assert/strict');
const agenda = require('../src/trading_radar/dashboard_assets/agenda.js');
const job = {id:'a',is_active:true,application:{status:'To Apply',next_action:'Relire',next_action_date:'2027-01-01'},deadline:{precision:'date',day:'2027-01-02'}};
test('Paris calendar day survives UTC midnight and inclusive day deadlines',()=>{
 assert.equal(agenda.parisDay('2027-01-01T23:30:00Z'),'2027-01-02');
 const list=agenda.entries([job],'2027-01-01T23:30:00Z');
 assert.equal(list[0].overdue,true);assert.equal(list[1].overdue,false);
});
test('applied jobs keep next actions and remove deposit deadlines',()=>{
 const list=agenda.entries([{...job,application:{...job.application,status:'Applied'}}],'2027-01-01T10:00:00Z');
 assert.equal(list.length,1);assert.equal(list[0].kind,'action');
 assert.equal(agenda.entries([{...job,application:{...job.application,status:'Offer'}}],'2027-01-01T10:00:00Z').length,1);
 assert.equal(agenda.entries([{...job,application:{...job.application,status:'Closed'}}],'2027-01-01T10:00:00Z').length,0);
});
test('conflicting deadlines never create false urgency',()=>{
 const list=agenda.entries([{...job,application:{status:'New'},deadline:{precision:'conflict',day:'2027-01-02'}}],'2027-01-01T10:00:00Z');
 assert.equal(list.length,0);
});
