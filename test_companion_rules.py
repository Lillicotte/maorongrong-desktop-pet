import unittest
from companion_rules import CompanionRules,SHORT_ACTIONS,IDLE_ACTIONS

class RNG:
    def __init__(self,choices=(),roll=.9):self.choices=list(choices);self.roll=roll
    def choice(self,pool):
        value=self.choices.pop(0) if self.choices else pool[0]
        assert value in pool,(value,pool)
        return value
    def random(self):return self.roll

class RulesTests(unittest.TestCase):
    def make(self,**kw):return CompanionRules(0,**kw)
    def settled(self,r,now=0):r.settled(r.revision,r.state,now)
    def enter(self,r,n,now=0,**kw):r.enter(n,now,**kw);self.settled(r,now)
    def test_neglect_branches_and_no_auto_reset(self):
        for branch in (10,14):
            r=self.make(rng=RNG([branch]));r.tick(300)
            self.assertEqual(r.state,branch);self.assertEqual(r.last_interaction,0)
    def test_thirty_second_actions(self):
        r=self.make(rng=RNG([25,17,10]));r.tick(29.999);self.assertEqual(r.state,0)
        r.tick(30);self.assertEqual(r.state,25);self.settled(r,31.2)
        r.tick(34.28);self.assertEqual(r.state,0);self.assertEqual(r.energy,79)
        r.tick(59.99);self.assertEqual(r.state,0);r.tick(60);self.assertEqual(r.state,17)
        self.settled(r,61.2);r.tick(64.28);self.assertEqual(r.state,0)
        r.tick(300);self.assertEqual(r.state,10)
    def test_sadness_and_cry(self):
        r=self.make();self.enter(r,10);r.tick(299.99);self.assertEqual(r.state,10)
        r.tick(300);self.assertEqual(r.state,24);before=r.affection
        r.left_click(301);self.assertEqual(r.state,10);self.assertEqual(r.affection,before+2)
    def test_sad_click_routes(self):
        for target in (4,11):
            r=self.make(rng=RNG([target]));self.enter(r,10);r.left_click(1)
            self.assertEqual(r.state,target);self.settled(r,1)
            if target==4:r.tick(4.08);self.assertEqual(r.state,0)
            else:r.left_click(2);self.assertEqual(r.state,15)
    def test_both_puff_branches(self):
        for target in (7,9):
            r=self.make(rng=RNG([target]));self.enter(r,15);r.left_click(1)
            self.assertEqual(r.state,target)
    def test_anger_lock_and_fire(self):
        r=self.make();self.enter(r,7);before=(r.affection,r.last_interaction,r.revision)
        self.assertFalse(r.left_click(20));self.assertFalse(r.button('feed',20));self.assertFalse(r.emotion_box(20));self.assertFalse(r.select(25,20))
        self.assertEqual(before,(r.affection,r.last_interaction,r.revision))
        r.tick(59.99);self.assertEqual(r.state,7);r.tick(60);self.assertEqual(r.state,9)
        r.left_click(61);self.assertEqual(r.state,0)
    def test_confusion_sweat_fear(self):
        r=self.make();self.enter(r,14);r.tick(60);self.assertEqual(r.state,16)
        self.settled(r,60);r.tick(359.99);self.assertEqual(r.state,16)
        r.tick(360);self.assertEqual(r.state,22);r.left_click(361);self.assertEqual(r.state,19)
        self.settled(r,361);r.tick(364.08);self.assertEqual(r.state,10)
    def test_sweat_click_shock(self):
        r=self.make();self.enter(r,16);r.left_click(1);self.assertEqual(r.state,18)
        self.settled(r,1);r.tick(4.08);self.assertEqual(r.state,0)
    def test_all_seven_auto_actions(self):
        self.assertEqual(set(IDLE_ACTIONS),{25,23,21,17,12,6,4})
        for target in IDLE_ACTIONS:
            r=self.make(rng=RNG([target]));r.tick(30);self.assertEqual(r.state,target)
            self.settled(r,30);r.tick(33.08);self.assertEqual(r.state,0)
    def test_party_is_thirty_seconds(self):
        r=self.make(affection=100,hunger=100,energy=100);r.tick(0);self.assertEqual(r.state,20)
        self.settled(r,0);r.tick(29.99);self.assertEqual(r.state,20)
        r.tick(30);self.assertEqual(r.state,0);r.tick(30.01);self.assertEqual(r.state,0)
    def test_reward_can_trigger_party(self):
        for kind,aff,hunger in [('pat',90,100),('feed',95,80)]:
            r=self.make(affection=aff,hunger=hunger,energy=100);r.button(kind,0);self.assertEqual(r.state,20)
    def test_nonclick_probabilities_and_rewards(self):
        for roll,target in [(0,2),(.4999,2),(.5,3),(.5999,3),(.6,0),(.999,0)]:
            r=self.make(rng=RNG(roll=roll));r.button('pat',0);self.assertEqual(r.affection,40)
            self.settled(r,0);r.tick(3.08);self.assertEqual(r.state,target);self.assertEqual(r.energy,79)
        r=self.make();r.button('feed',0);self.assertEqual((r.affection,r.hunger),(35,95))
    def test_flower_freezes_all_losses(self):
        r=self.make();self.enter(r,3);before=(r.affection,r.hunger,r.energy)
        r.tick(30,moving=True);r.tick(59.99,moving=True);self.assertEqual(before,(r.affection,r.hunger,r.energy))
        r.tick(60,moving=True);self.assertEqual(r.state,0)
        r.tick(120,allow_auto=False);self.assertEqual(r.hunger,74)
    def test_idle_stats_and_interaction_reset(self):
        r=self.make();r.tick(60,allow_auto=False);self.assertEqual((r.affection,r.hunger,r.energy),(30,74,80))
        r.tick(120,allow_auto=False);self.assertEqual((r.affection,r.hunger,r.energy),(29,73,80))
        r.note_interaction(120);r.tick(239.9,allow_auto=False);self.assertEqual(r.affection,29)
    def test_sleep_recovers_and_deepens(self):
        r=self.make(energy=0);r.button('sleep',0);self.settled(r,0)
        r.tick(29.99);self.assertEqual(r.state,5);r.tick(30);self.assertEqual(r.state,8)
        self.assertEqual(r.transition_clip,'05_to_08');self.settled(r,30);r.tick(60);self.assertEqual(r.energy,4)
    def test_exhaustion_rests(self):
        r=self.make(energy=1);self.enter(r,4);r.tick(3.08);self.assertEqual((r.state,r.energy),(26,0))
        r.button('sleep',4);self.assertEqual(r.state,5)
    def test_click_affinity_pools_and_rewards(self):
        cases=[(19,11),(19,15),(20,4),(70,25),(71,21),(71,4),(71,12),(71,6)]
        for level,target in cases:
            r=self.make(affection=level,rng=RNG([target]));r.left_click(0)
            self.assertEqual(r.state,target);self.assertEqual(r.affection,min(100,level+2))
    def test_emotion_box_applies_state_followups(self):
        for target in range(1,27):
            r=self.make(rng=RNG([target]));r.emotion_box(0);self.assertEqual(r.state,target);self.settled(r)
            if target==1:self.assertTrue(r.quiet)
            if target==19:r.tick(3.08);self.assertEqual(r.state,10)
            if target==14:r.tick(60);self.assertEqual(r.state,16)
            if target==3:r.tick(60);self.assertEqual(r.state,0)
    def test_quiet_and_stale_callbacks(self):
        r=self.make();r.set_quiet(True,0);r.tick(1000);self.assertEqual(r.state,1)
        self.assertFalse(r.left_click(1000));self.assertFalse(r.button('pat',1000))
        r.select(0,1000);self.assertFalse(r.quiet)
        r.enter(4,1001);rev=r.revision;r.enter(10,1002);r.settled(rev,4,1003)
        self.assertIsNone(r.deadline)
    def test_settings_overlay_does_not_break_chains(self):
        r=self.make();self.enter(r,14);r.tick(60,allow_auto=False);self.assertEqual(r.state,16)
        r=self.make();r.tick(400,allow_auto=False);self.assertEqual(r.state,0)
    def test_action_cost_cannot_be_evaded_by_interrupting(self):
        r=self.make();r.enter(4,0);self.assertEqual(r.energy,79)
        r.enter(6,.1);self.assertEqual(r.energy,78)
        r.enter(0,.2);self.assertEqual(r.energy,78)
    def test_movement_cost_accumulates_across_walks(self):
        r=self.make();r.tick(4,moving=True,allow_auto=False)
        r.tick(40,allow_auto=False);self.assertEqual(r.energy,80)
        r.tick(46,moving=True,allow_auto=False);self.assertEqual(r.energy,79)
    def test_zero_energy_manual_normal_is_still_rest(self):
        r=self.make(energy=0);r.select(0,0);self.assertEqual(r.state,26)
        r.select(5,1);self.assertEqual(r.state,5)

if __name__=='__main__':unittest.main(verbosity=2)
