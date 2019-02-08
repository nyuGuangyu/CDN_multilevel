import cPickle as cp
import sys
import numpy as np
from Popularity_estimator import *
from Multilevel_graph import *
from Policy_evaluator import *

directory = '/home/lgy/CDN_multilevel/data/'
test_day = 7
segment = 240000
subtree = '0011101001000100'

# generated train,test data
reqlist_train = []
reqlist_test = []
print 'Collecting data ...'
print "-"*100
filename = directory + 'day'+ str(test_day)+'reqlist.cp'
with open(filename,'rb') as infile:
        reqlist = cp.load(infile)

cnt = 0
cnt_sub_train = 0
cnt_sub_test = 0
for req in reqlist:
    if  cnt <=segment:
        reqlist_train.append(req)
        if req[1][:16] == subtree:
            cnt_sub_train += 1
    elif cnt <= 2*segment:
        reqlist_test.append(req)
        if req[1][:16] == subtree:
            cnt_sub_test += 1
    else:
        break
    cnt += 1
print "train:",cnt_sub_train
print 'test:',cnt_sub_test

# get popularity estimate from training data
# choose sub-tree in prefix = 16, then filter reqlist_train reqlist_test
UP_LEVEL_PREFIX = 16
MID_LEVEL_PREFIX = 18
BOTTOM_LEVEL_PREFIX = 20
print "network struct,UP,MID,BOTTOM:",UP_LEVEL_PREFIX,MID_LEVEL_PREFIX,BOTTOM_LEVEL_PREFIX

# print 'finding all sub-trees of prefix',UP_LEVEL_PREFIX
# ip_occurance = {}
# for req in reqlist_train:
#     if req[1][:UP_LEVEL_PREFIX] not in ip_occurance:
#         ip_occurance[req[1][:UP_LEVEL_PREFIX]] = 1
#     else:
#         ip_occurance[req[1][:UP_LEVEL_PREFIX]] += 1
#
# sub_list = [sub for sub in ip_occurance if ip_occurance[sub]>2000]
# if not sub_list:
#     print 'req number limit too high, reduce the limit !'

opt_d_b = 50.
opt_d_h_mid = 5.5
opt_d_h_up = 11.
opt_d_m_mid = 55.
opt_d_m_up = 110.


pop = Popularity_estimator(reqlist_train,BOTTOM_LEVEL_PREFIX)
print 'Calculating global pop...'
pop.calculate_global_pop()
print 'Calculating MF pop...'
pop.calculate_MF_pop()

# generate graph from training data
lf = 16 # everytime you change lf, remember to run static placement again!!
cache_catalog_percent = 0.7
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
print 'segment:',segment
print 'cache_size_multiplier:',lf
print 'evaluating sub-tree id: ' + subtree + ' with req number:', cnt_sub_test
ev.evaluate(static_caching=True)
# ev.evaluate(static_caching=False,MFLRU=True)




