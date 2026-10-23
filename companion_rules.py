"""Cat companionship rules. All times are monotonic seconds supplied by the UI."""
import random

SHORT_ACTIONS={4,6,12,17,18,19,21,23,25}
IDLE_ACTIONS=(25,23,21,17,12,6,4)
TIMED_STATES={3:60,7:60,10:300,14:60,16:300,20:30}

class CompanionRules:
    def __init__(self,now,affection=30,hunger=75,energy=80,rng=None):
        self.affection=max(0,min(100,int(affection)))
        self.hunger=max(0,min(100,int(hunger)))
        self.energy=max(0,min(100,int(energy)))
        self.rng=rng or random
        self.state=0;self.revision=0;self.quiet=False
        self.entered_at=now;self.stable_at=now;self.deadline=None
        self.sleep_started_at=None;self.transition_clip=None
        self.last_interaction=now;self.next_auto=now+30
        self._last_tick=now;self._aff_elapsed=0.;self._hunger_elapsed=0.
        self._sleep_elapsed=0.;self._activity_elapsed=0.
        self._full_latched=False
        self.temporary=False;self.return_to=0;self.post_reaction=False;self.action_cost=0

    @property
    def sleeping(self):return self.state in (5,8)

    @property
    def flower(self):return self.state==3

    def left_locked(self,now):
        return self.state==7 and (self.deadline is None or now<self.deadline)

    def _accrue(self,now,moving=False):
        elapsed=max(0,now-self._last_tick);self._last_tick=now
        if self.flower:return
        self._hunger_elapsed+=elapsed
        self._aff_elapsed+=elapsed
        loss=int(self._hunger_elapsed//60);self._hunger_elapsed%=60
        self.hunger=max(0,self.hunger-loss)
        loss=int(self._aff_elapsed//120);self._aff_elapsed%=120
        self.affection=max(0,self.affection-loss)
        if self.sleeping:
            self._sleep_elapsed+=elapsed
            gain=int(self._sleep_elapsed//15);self._sleep_elapsed%=15
            self.energy=min(100,self.energy+gain)
        else:self._sleep_elapsed=0
        if moving or self.state==20:
            self._activity_elapsed+=elapsed
            loss=int(self._activity_elapsed//10);self._activity_elapsed%=10
            self.energy=max(0,self.energy-loss)

    def note_interaction(self,now):
        self._accrue(now)
        self.last_interaction=now;self.next_auto=now+30;self._aff_elapsed=0.

    def enter(self,n,now,*,temporary=None,return_to=0,post_reaction=False,action_cost=None,transition_clip=None):
        if self.quiet and n!=1:return False
        self._accrue(now)
        self.state=n;self.revision+=1;self.entered_at=now
        self.stable_at=now if n==0 else None;self.deadline=None;self.sleep_started_at=None
        self.transition_clip=transition_clip
        self.temporary=(n in SHORT_ACTIONS) if temporary is None else temporary
        self.return_to=return_to;self.post_reaction=post_reaction
        self.action_cost=(1 if self.temporary else 0) if action_cost is None else action_cost
        if self.action_cost:
            self.energy=max(0,self.energy-self.action_cost)
            self.action_cost=0
            if self.energy<=0:
                self.state=26;self.temporary=False;self.post_reaction=False;self.return_to=0
        if n==0 and self.next_auto<=now:self.next_auto=now+30
        return True

    def settled(self,revision,n,now):
        if revision!=self.revision or n!=self.state or self.stable_at is not None:return
        self.stable_at=now
        if self.temporary:self.deadline=now+3.08
        elif n in TIMED_STATES:self.deadline=now+TIMED_STATES[n]
        if n==5:self.sleep_started_at=now

    def _party(self,now):
        full=min(self.affection,self.hunger,self.energy)>=100
        if not full:
            if self.state!=20:self._full_latched=False
            return False
        if self.state==20 or self._full_latched or self.quiet or self.left_locked(now):return False
        self._full_latched=True
        return self.enter(20,now)

    def _reaction(self,now):
        roll=self.rng.random()
        return self.enter(2 if roll<.5 else 3 if roll<.6 else 0,now)

    def tick(self,now,*,moving=False,allow_auto=True,busy=False,pinned=False):
        self._accrue(now,moving)
        if self.quiet:return
        if self.energy<=0 and not self.sleeping and self.state!=26 and not self.left_locked(now):
            self.enter(26,now);return
        if pinned:return
        if allow_auto and self._party(now):return
        if self.state==5 and self.sleep_started_at is not None and now-self.sleep_started_at>=30:
            self.enter(8,now,transition_clip='05_to_08');return
        if self.deadline is not None and now>=self.deadline:
            if self.temporary:
                if self.energy<=0:self.enter(26,now)
                elif self.post_reaction:self._reaction(now)
                else:self.enter(self.return_to,now)
            else:self.enter({7:9,10:24,14:16,16:22,3:0,20:0}[self.state],now)
            return
        if self.state==0 and allow_auto and not busy:
            if now-self.last_interaction>=300:
                self.enter(self.rng.choice((10,14)),now)
            elif now>=self.next_auto:
                self.next_auto=now+30
                self.enter(self.rng.choice(IDLE_ACTIONS),now)

    def left_click(self,now):
        if self.quiet or self.left_locked(now):return False
        self.note_interaction(now);level=self.affection
        self.affection=min(100,self.affection+2)
        if self._party(now):return True
        if self.energy<=0:return self.enter(26,now)
        state=self.state
        if state==24:return self.enter(10,now)
        if state==10:return self.enter(self.rng.choice((4,11)),now)
        if state==11:return self.enter(15,now)
        if state==15:return self.enter(self.rng.choice((7,9)),now)
        if state==9:return self.enter(0,now)
        if state==16:return self.enter(18,now)
        if state==22:return self.enter(19,now,return_to=10)
        pool=(11,15) if level<20 else (21,4,12,6) if level>70 else (4,12,6,23,25)
        return self.enter(self.rng.choice(pool),now)

    def button(self,kind,now):
        if self.quiet or self.left_locked(now):return False
        self.note_interaction(now)
        if kind=='sleep':
            if self.sleeping:return self.enter(25,now,post_reaction=True)
            if self._party(now):return True
            return self.enter(5,now)
        if kind=='pat':self.affection=min(100,self.affection+10);target=25;cost=1
        elif kind=='feed':self.affection=min(100,self.affection+5);self.hunger=min(100,self.hunger+20);target=6;cost=1
        elif kind=='play':self.affection=min(100,self.affection+5);target=25;cost=5
        else:raise ValueError(kind)
        if self._party(now):return True
        if self.energy<=0:return self.enter(26,now)
        return self.enter(target,now,post_reaction=True,action_cost=cost)

    def emotion_box(self,now):
        if self.quiet or self.left_locked(now):return False
        self.note_interaction(now)
        target=self.rng.choice(tuple(range(1,27)))
        return self.select(target,now,from_box=True)

    def select(self,n,now,from_box=False):
        if self.left_locked(now) and n!=1:return False
        self.note_interaction(now);self.quiet=n==1
        if self.energy<=0 and n not in (1,5,8,26):n=26
        return self.enter(n,now,return_to=10 if from_box and n==19 else 0)

    def set_quiet(self,value,now):
        self.note_interaction(now);self.quiet=bool(value)
        return self.enter(1 if value else 26 if self.energy<=0 else 0,now)
