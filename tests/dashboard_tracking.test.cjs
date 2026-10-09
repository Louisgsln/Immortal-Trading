const test=require('node:test');const assert=require('node:assert/strict');
global.radarAgenda=require('../src/trading_radar/dashboard_assets/agenda.js');
const tracking=require('../src/trading_radar/dashboard_assets/tracking.js');
const job={is_active:true,is_expired:false};
test('prepare uses the Paris day and leaves the original tracking untouched',()=>{
 const application={status:'Reviewing',notes:'Keep',next_action:'Previous',next_action_date:'2026-11-01'};
 const before=JSON.stringify(application);
 const actions=tracking.shortcuts(job,application,'2026-10-09T23:30:00Z');
 assert.deepEqual(actions.find(a=>a.id==='prepare').changes,{status:'To Apply',next_action:'Préparer et envoyer la candidature',next_action_date:'2026-10-10'});
 assert.equal(JSON.stringify(application),before);
});
test('follow-up uses calendar days across Paris daylight saving and year changes',()=>{
 for(const [now,expected] of [['2026-10-24T22:30:00Z','2026-11-01'],['2026-12-30T23:30:00Z','2027-01-07']]){
  const action=tracking.shortcuts(job,{status:'Applied'},now).find(a=>a.id==='followup');
  assert.deepEqual(action.changes,{next_action:'Relancer le recrutement',next_action_date:expected});
 }
});
test('completed action clears text and date without changing application status',()=>{
 const action=tracking.shortcuts(job,{status:'Interview',next_action:'Prepare',next_action_date:'2026-10-11'},'2026-10-09T08:00:00Z').find(a=>a.id==='complete');
 assert.deepEqual(action.changes,{next_action:null,next_action_date:null});
});
test('no preparation shortcut for closed, expired or already submitted offers',()=>{
 const now='2026-10-09T08:00:00Z';
 for(const j of [{...job,is_active:false},{...job,is_expired:true}])assert.equal(tracking.shortcuts(j,{status:'New'},now).length,0);
 for(const status of ['Applied','Rejected','Withdrawn','Closed','Offer','Interview'])assert.ok(!tracking.shortcuts(job,{status},now).some(a=>a.id==='prepare'));
});
