const test=require('node:test');const assert=require('node:assert/strict');
const prefs=require('../src/trading_radar/dashboard_assets/preferences.js');
function memory(){const m=new Map();return {getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,v),removeItem:k=>m.delete(k)};}
const options={programme:['','off_cycle','long'],'programme-year':['','2027','unknown','conflict'],country:['','FR','GB'],score:['0','70'],active:['available','all'],sort:['score','recent']};
test('separate views survive reload without storing tracking or access credentials',()=>{
 const storage=memory();assert.equal(prefs.load(storage,options).status,'empty');
 assert.ok(prefs.save(storage,{jobs:{programme:'off_cycle',country:'FR',notes:'private note',token:'secret',url:'secret'},applications:{active:'all',score:'0'}},options));
 assert.deepEqual(prefs.load(storage,options).views,{jobs:{programme:'off_cycle',country:'FR'},applications:{score:'0',active:'all'}});
 assert.ok(prefs.clear(storage));assert.equal(prefs.load(storage,options).status,'empty');
});
test('unavailable options and malformed calendar periods fall back to defaults',()=>{
 const storage=memory();prefs.save(storage,{jobs:{country:'DE','start-from':'2027-02-30','publication-from':'2027-03-02','publication-to':'2027-03-01',score:'nan',search:'a'.repeat(501)}},options);
 assert.deepEqual(prefs.load(storage,options).views.jobs,{});
 prefs.save(storage,{jobs:{country:'FR','start-from':'2028-02-29'}},options);
 assert.deepEqual(prefs.load(storage,{...options,country:['GB']}).views.jobs,{'start-from':'2028-02-29'});
});
test('storage denial and corruption never prevent Dashboard consultation',()=>{
 const denied={getItem(){throw Error('denied')},setItem(){throw Error('full')},removeItem(){throw Error('denied')}};
 assert.equal(prefs.load(denied,options).status,'unavailable');assert.equal(prefs.save(denied,{},options),false);assert.equal(prefs.clear(denied),false);
 const broken=memory();broken.setItem('radar-consultation-v1','{bad');assert.equal(prefs.load(broken,options).status,'unavailable');
 broken.setItem('radar-consultation-v1',JSON.stringify({version:2,views:{}}));assert.equal(prefs.load(broken,options).status,'invalid');
});
test('untrusted saved objects cannot add fields or prototypes',()=>{
 const storage=memory();storage.setItem('radar-consultation-v1','{"version":1,"views":{"jobs":{"__proto__":{"evil":true},"country":"FR"},"__proto__":{"evil":true}}}');
 assert.deepEqual(prefs.load(storage,options).views,{jobs:{country:'FR'}});assert.equal({}.evil,undefined);
});

test('programme year is retained per view and unavailable years are discarded',()=>{
 const storage=memory();prefs.save(storage,{jobs:{'programme-year':'2027'},applications:{'programme-year':'unknown'}},options);
 assert.deepEqual(prefs.load(storage,options).views,{jobs:{'programme-year':'2027'},applications:{'programme-year':'unknown'}});
 assert.deepEqual(prefs.load(storage,{...options,'programme-year':['','unknown']}).views,{jobs:{},applications:{'programme-year':'unknown'}});
});
