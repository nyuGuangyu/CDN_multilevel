import cPickle as cp
import sys
import numpy as np
from Popularity_estimator import *
from Multilevel_graph import *
from Policy_evaluator import *
from dateutil import parser
from operator import itemgetter

directory = '/home/gl1257/CDN_multilevel/data/'
test_day = 7
test_length = 2
train_length = 8 # hours
subtree = '1101001101100110'

UP_LEVEL_PREFIX = 16
MID_LEVEL_PREFIX = 18
BOTTOM_LEVEL_PREFIX = 20
print "network struct,UP,MID,BOTTOM:",UP_LEVEL_PREFIX,MID_LEVEL_PREFIX,BOTTOM_LEVEL_PREFIX

opt_d_b = 50.
opt_d_h_mid = 5.5
opt_d_h_up = 11.
opt_d_m_mid = 55.
opt_d_m_up = 110.
lf = 4 # everytime you change lf, remember to run static placement again!!
cache_catalog_percent = 0.3


# generated train,test data

print 'Collecting data ...'
print "-"*100
filename = directory + 'day'+ str(test_day)+'reqlist.cp'
with open(filename,'rb') as infile:
        reqlist = cp.load(infile)

# sub_reqs = {}
# for req in reqlist:
#     sub = req[1][:16]
#     if sub not in sub_reqs:
#         sub_reqs[sub] = 1
#     else:
#         sub_reqs[sub] += 1
# target = sorted(sub_reqs.items(),key=itemgetter(1),reverse=True)[0][0]
# print target
# sys.exit()


reqs_segment = {}
for req in reqlist:
    hr = parser.parse(req[0]).hour
    if hr not in reqs_segment:
        reqs_segment[hr] = [req]
    else:
        reqs_segment[hr].append(req)
print [len(reqs_segment[key]) for key in reqs_segment]

reqs_train = []
reqs_test = []
for h in range(train_length,24-test_length):
    seg_a = []
    seg_b = []
    for a in range(h-train_length,train_length):
        seg_a += reqs_segment[a]
    for b in range(h,h+test_length):
        seg_b += reqs_segment[b]
    reqs_train.append(seg_a)
    reqs_test.append(seg_b)
print 'segment number=', len(reqs_train), len(reqs_test)

cnt_dbs_glb = []
cnt_dhms_glb = []
cnt_dhup_glb = []
cnt_dbs_mf = []
cnt_dhms_mf = []
cnt_dhup_mf = []
for s,reqs in enumerate(reqs_test):
    reqlist_train = reqs_train[s]
    def check_trainable(reqlist_train,limit):
        req_freq = {}
        for req in reqlist:
            content = req[2]
            if content not in req_freq:
                req_freq[content] = 1
            else:
                req_freq[content] += 1

    reqlist_test = reqs
    # get popularity estimate from training data
    pop = Popularity_estimator(reqlist_train,BOTTOM_LEVEL_PREFIX)
    print 'Calculating global pop for seg:',s
    pop.calculate_global_pop()
    print 'Calculating MF pop for seg:',s
    pop.calculate_MF_pop()

    # generate graph from training data
    lv3graph = level3_graph(pop,cache_catalog_percent,subtree,
                            level_factor =lf,
                            d_b = opt_d_b,
                            d_h_mid = opt_d_h_mid,
                            d_h_up = opt_d_h_up,
                            d_m_mid = opt_d_m_mid,
                            d_m_up = opt_d_m_up,
                            UP_LEVEL_PREFIX=UP_LEVEL_PREFIX,
                            MID_LEVEL_PREFIX=MID_LEVEL_PREFIX,
                            BOTTOM_LEVEL_PREFIX=BOTTOM_LEVEL_PREFIX)

    # update according to which method...
    lv3graph.update_static_placement_routing()
    # lv3graph.get_initial_MFLRU_placement(reqlist_train,propotion=0.)

    # evaluate avg delay
    ev = policy_evaluator(reqlist_test,subtree,lv3graph, UP_LEVEL_PREFIX,
                            d_b = opt_d_b,
                            d_h_mid = opt_d_h_mid,
                            d_h_up = opt_d_h_up,
                            d_m_mid = opt_d_m_mid,
                            d_m_up = opt_d_m_up)
    print '-'*80
    print 'cache_size_multiplier:',lf
    print 'evaluating sub-tree id: ' + subtree + ' with req number:', len(reqlist_test)
    ev.evaluate(static_caching=True)
    # ev.evaluate(static_caching=False,MFLRU=True)

    cnt_dbs_glb.append(ev.cnt_list[0][0])
    cnt_dhms_glb.append(ev.cnt_list[0][1])
    cnt_dhup_glb.append(ev.cnt_list[0][2])

    cnt_dbs_mf.append(ev.cnt_list[1][0])
    cnt_dhms_mf.append(ev.cnt_list[1][1])
    cnt_dhup_mf.append(ev.cnt_list[1][2])

print 'train_length:',train_length,'test_length:',test_length
print cnt_dbs_glb
print cnt_dhms_glb
print cnt_dhup_glb
print cnt_dbs_mf
print cnt_dhms_mf
print cnt_dhup_mf



