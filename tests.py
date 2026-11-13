import os,unittest; os.environ["GR_DB"]="test.db"
import server as S
class T(unittest.TestCase):
    def setUp(s): S.init(True)
    def test1_rescue_capacity(s):
        r=S.rescue("B1"); s.assertEqual(r["affected"],40); s.assertEqual(r["accommodated"]+r["waiting"],40)
        for v in S.q("select id from vehicles"): s.assertGreaterEqual(S.free(v["id"]),0)
    def test2_closed_edge(s):
        r=S.road_close("Junction","College"); s.assertFalse(r["uses_closed"]); s.assertTrue(S.route("Kalpur","College"))
    def test3_surge(s):
        r=S.capacity(80); s.assertEqual(r["demand"],146); s.assertEqual(r["allocated"]+r["unallocated"],146); s.assertEqual(r["unallocated"],r["demand"]-r["allocated"]); s.assertGreater(r["unallocated"],0)
    def test4_report(s): S.intent("my bus has not arrived"); s.assertTrue(S.state()["reports"])
    def test5_book(s):
        S.rescue("B1"); b=S.q("select id from vehicles where id='B2'",one=True); f=S.free("B2"); r=S.book("Mudhol"); s.assertTrue(r["ref"] or f==0)
    def test6_persist(s): S.book("Kalpur"); n=S.state()["students"]; S.init(); s.assertEqual(S.state()["students"],n)
    def test7_request_capacity(s):
        r=S.request_ride({"name":"A","village":"Kalpur","seats":10,"problem":"bus","bus":"B1"})
        s.assertEqual(r["allocated"]+r["waiting"],10)
        for v in S.q("select id from vehicles"): s.assertGreaterEqual(S.free(v["id"]),0)
        s.assertNotIn("B1",[x["id"] for x in r["vehicles"]]); s.assertEqual(S.track(r["ref"])["ref"],r["ref"])
    def test8_road_avoided(s):
        r=S.request_ride({"name":"A","village":"Kalpur","seats":1,"problem":"road","road":["Junction","College"]})
        p=r["route"]["path"]; s.assertFalse(any({p[i],p[i+1]}=={"Junction","College"} for i in range(len(p)-1)))
    def test9_intent_say(s):
        r=S.intent("how many seats are free"); s.assertIn("seats",r["say"]); s.assertIn("Reference",S.intent("book a seat from Mudhol")["say"])
        s.assertEqual(S.intent("blah")["intent"],"unknown")
    def test10_exam_crisis(s):
        r=S.exam_crisis(); s.assertEqual(r["demand"],r["scenario"]["base_students"]+r["scenario"]["surge_added"])
        s.assertEqual(r["seated"]+r["unallocated"],r["demand"])
        for v in r["vehicles"]: s.assertLessEqual(v["seated"],v["cap"]); s.assertNotIn(v["id"],("B1","B2"))
        s.assertEqual(r["exam_seated"],r["exam_total"]); s.assertTrue(S.q("select 1 from edges where a='Junction' and b='College' and blocked=1"))
        s.assertEqual(S.intent("how many students waiting")["intent"],"waiting"); s.assertIn("Exam in 60",S.intent("exam in 60 minutes from Mudhol")["say"])
if __name__=="__main__": unittest.main()
