import unittest
from dataclasses import replace
from matchdesk.engine import Session, generate, claim, verify, visible

class EngineTests(unittest.TestCase):
    def test_repeatable(self):
        self.assertEqual(generate(7),generate(7))
        self.assertNotEqual(generate(7),generate(8))
    def test_no_future_evidence(self):
        s=Session(); snapshot=s.snapshot(600)
        self.assertTrue(all(e['second']<=600 for e in snapshot['events']))
        for c in snapshot['cards']:
            self.assertTrue(c['verified'])
            self.assertTrue(set(c['claim']['evidence_ids'])<=set(e['id'] for e in snapshot['events']))
    def test_wrong_team_value_window_and_evidence_rejected(self):
        events=generate();clock=events[-1].second;c=claim(events,'Harbour',0,clock)
        for field,value in [('value',999),('end',clock+1),('team','Unknown'),('evidence_ids',[])]:
            self.assertFalse(verify({**c,field:value},events,clock))
    def test_correction_invalidates_old_claim_and_updates_count(self):
        s=Session();e=next(e for e in s.events.values() if e.kind=='shot' and not e.goal)
        clock=e.second;old=claim(list(s.events.values()),e.team,0,clock)
        s.correct_shot(e.id)
        self.assertFalse(verify(old,list(s.events.values()),clock))
        new=claim(list(s.events.values()),e.team,0,clock)
        self.assertEqual(new['value'],old['value']-1)
        self.assertTrue(verify(new,list(s.events.values()),clock))
        self.assertEqual(len(s.audit),1)
    def test_duplicate_is_idempotent_and_conflict_rejected(self):
        s=Session();e=next(iter(s.events.values()));n=len(s.events)
        self.assertFalse(s.ingest(e));self.assertEqual(len(s.events),n)
        with self.assertRaises(ValueError):s.ingest(replace(e,second=e.second+1))
    def test_session_isolation(self):
        a,b=Session(),Session();e=next(e for e in a.events.values() if e.kind=='shot' and not e.goal)
        a.correct_shot(e.id);self.assertEqual(b.events[e.id].kind,'shot')
    def test_cannot_remove_goal_with_simple_correction(self):
        s=Session();e=next(e for e in s.events.values() if e.goal)
        with self.assertRaises(ValueError):s.correct_shot(e.id)

if __name__=='__main__':unittest.main()
