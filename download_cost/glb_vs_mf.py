import cPickle as cp
import sys
import numpy as np
from Popularity_estimator import *
from Multilevel_graph import *
from Policy_evaluator import *
from dateutil import parser
from operator import itemgetter

directory = '/home/lgy/CDN_multilevel/data/'
test_day = 7
train_length = 8 # hours
test_length = 2
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
    for a in range(h-train_length,h):
        seg_a += reqs_segment[a]
    for b in range(h,h+test_length):
        seg_b += reqs_segment[b]
    reqs_train.append(seg_a)
    reqs_test.append(seg_b)
print 'segment number=', len(reqs_train), len(reqs_test)
print [len(e) for e in reqs_train]
print [len(e) for e in reqs_test]

distances_glb = []
distances_mf = []
for s,reqs in enumerate(reqs_test):
    reqlist_train = reqs_train[s]
    reqlist_test = reqs
    # get popularity estimate from training data
    pop = Popularity_estimator(reqlist_train,BOTTOM_LEVEL_PREFIX)
    print 'Calculating global pop for seg:',s
    pop.calculate_global_pop()
    print 'Calculating MF pop for seg:',s
    pop.calculate_MF_pop()

    sub_it_freq = {}
    for req in reqlist_test:
        if req[:UP_LEVEL_PREFIX] == subtree:
            sub = req[:BOTTOM_LEVEL_PREFIX]
            if sub not in sub_it_freq:
                sub_it_freq[sub] = {}
                sub_it_freq[sub][req[2]] = 1
            else:
                if req[2] not in sub_it_freq[sub]:
                    sub_it_freq[sub][req[2]] = 1
                else:
                    sub_it_freq[sub][req[2]] += 1
