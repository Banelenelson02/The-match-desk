"""Exact event processing. No model output is treated as ground truth."""
from dataclasses import asdict, dataclass, replace
from random import Random

@dataclass(frozen=True)
class Event:
    id: str
    second: int
    team: str
    player: str
    kind: str
    complete: bool = False
    goal: bool = False

def generate(seed=42):
    """Repeatable illustrative possessions, not a calibrated football model."""
    rng = Random(seed)
    events = []
    second = 0
    for possession in range(60):
        team = ('Harbour', 'Valley')[possession % 2]
        for action in range(rng.randint(3, 7)):
            second += rng.randint(5, 15)
            kind = 'shot' if action == 2 and possession % 4 == 0 else 'pass'
            events.append(Event(f'e{len(events)+1:04}', second, team,
                                f'{team} {rng.randint(2,11)}', kind,
                                complete=kind == 'pass' and rng.random() < .8,
                                goal=kind == 'shot' and possession in (8, 28, 44)))
        second += 12
        events.append(Event(f'e{len(events)+1:04}', second, team, f'{team} 6', 'turnover'))
    return events

def visible(events, clock):
    return sorted((e for e in events if e.second <= clock), key=lambda e: (e.second, e.id))

def statistics(events):
    return {team: {'shots': sum(e.kind == 'shot' for e in events if e.team == team),
                   'goals': sum(e.kind == 'shot' and e.goal for e in events if e.team == team),
                   'passes': sum(e.kind == 'pass' for e in events if e.team == team),
                   'completed_passes': sum(e.kind == 'pass' and e.complete for e in events if e.team == team)}
            for team in ('Harbour', 'Valley')}

def claim(events, team, start, end):
    evidence = [e.id for e in events if e.team == team and e.kind == 'shot' and start <= e.second <= end]
    return {'team': team, 'metric': 'shots', 'start': start, 'end': end,
            'value': len(evidence), 'evidence_ids': evidence}

def verify(candidate, events, clock):
    """Validate the exact metric scope and the complete evidence set."""
    if candidate.get('metric') != 'shots' or candidate.get('team') not in ('Harbour','Valley'):
        return False
    start, end = candidate.get('start'), candidate.get('end')
    if type(start) is not int or type(end) is not int or not 0 <= start <= end <= clock:
        return False
    if type(candidate.get('value')) is not int:
        return False
    expected = claim(visible(events, clock), candidate['team'], start, end)
    return candidate == expected

class Session:
    def __init__(self, seed=42):
        self.events = {e.id: e for e in generate(seed)}
        self.audit = []

    def ingest(self, event):
        if event.id in self.events:
            if self.events[event.id] != event:
                raise ValueError('Conflicting duplicate; use an explicit correction')
            return False
        self.events[event.id] = event
        return True

    def correct_shot(self, event_id):
        old = self.events[event_id]
        if old.kind != 'shot' or old.goal:
            raise ValueError('Starter supports correcting non-goal shots only')
        self.events[event_id] = replace(old, kind='pass', complete=True)
        self.audit.append({'event_id': event_id, 'before': asdict(old),
                           'after': asdict(self.events[event_id]), 'reason': 'Simulated classification correction'})

    def snapshot(self, clock, audience='analyst'):
        events = visible(self.events.values(), clock)
        start = max(0, clock - 600)
        cards = []
        for team in ('Harbour', 'Valley'):
            c = claim(events, team, start, clock)
            text = (f"{team}: {c['value']} shots between {start//60}:{start%60:02} and {clock//60}:{clock%60:02}."
                    if audience == 'analyst' else f"{team} took {c['value']} shots in this spell.")
            cards.append({'id': f'{team}-{start}-{clock}', 'claim': c, 'text': text,
                          'verified': verify(c, events, clock), 'version': len(self.audit)+1,
                          'mode': 'deterministic_template', 'valid_until': clock+30})
        return {'clock': clock, 'events': [asdict(e) for e in events], 'stats': statistics(events),
                'cards': cards, 'audit': self.audit,
                'mode': 'local deterministic starter; AI agents not connected',
                'duration': max(e.second for e in self.events.values()),
                'recap': ' '.join(f"{t}: {s['goals']} goals and {s['shots']} shots." for t,s in statistics(events).items())}
