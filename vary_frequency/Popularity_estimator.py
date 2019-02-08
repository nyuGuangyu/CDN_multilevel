from collections import defaultdict
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.decomposition import NMF
import copy
import cPickle as cp
import os.path
import sys

COMPONENT = 50
COLD_ITEM_LIMIT_PERCENT = 0
COLD_SUBGROUP_LIMIT = 0
dir = '/home/gl1257/CDN_multilevel/vary_frequency/pops/'

class Popularity_estimator(object):
    def __init__(self,reqlist_train,BOTTOM_LEVEL_PREFIX):
        self.reqlist = reqlist_train
        self.subgroup_item_freq = defaultdict(dict)
        self.content_freq = {}
        self.global_pop = defaultdict(dict)
        self.MF_pop = defaultdict(dict)
        self.arrival_rate = {}
        self.BOTTOM_LEVEL_PREFIX = BOTTOM_LEVEL_PREFIX
        self.__get_rating_matrix()

    def __get_rating_matrix(self):
        for req in self.reqlist:
            time,ip,content = tuple(req)
            subgroup = ip[:self.BOTTOM_LEVEL_PREFIX]
            # subgroup_item_freq
            if subgroup not in self.subgroup_item_freq:
                 self.subgroup_item_freq[subgroup][content] = 1
            else:
                if content not in self.subgroup_item_freq[subgroup]:
                    self.subgroup_item_freq[subgroup][content] = 1
                else:
                    self.subgroup_item_freq[subgroup][content] += 1

        # more preprocess...
        print 'Removing subgroups whose requests are less than', COLD_SUBGROUP_LIMIT, '...'
        for subgroup in self.subgroup_item_freq.keys():
            if sum(self.subgroup_item_freq[subgroup].values()) < COLD_SUBGROUP_LIMIT:
                del self.subgroup_item_freq[subgroup]

        print 'Removing contents accessed less than', COLD_ITEM_LIMIT_PERCENT, '% other requests...'
        for subgroup in self.subgroup_item_freq:
            for item in self.subgroup_item_freq[subgroup]:
                if item not in self.content_freq:
                    self.content_freq[item] = self.subgroup_item_freq[subgroup][item]
                else:
                    self.content_freq[item] += self.subgroup_item_freq[subgroup][item]

        COLD_ITEM_LIMIT = np.percentile([e[1] for e in self.content_freq.items()],COLD_ITEM_LIMIT_PERCENT)

        for content,freq in self.content_freq.items():
            if freq < COLD_ITEM_LIMIT:
                del self.content_freq[content]
        its = set()
        for subgroup in self.subgroup_item_freq.keys():
            for item in self.subgroup_item_freq[subgroup].keys():
                if item not in self.content_freq:
                    del self.subgroup_item_freq[subgroup][item]
                    if not self.subgroup_item_freq[subgroup]:
                        del self.subgroup_item_freq[subgroup]
                else:
                    its.add(item)

        # get arrive rate:
        for subgroup in self.subgroup_item_freq:
            self.arrival_rate[subgroup] = sum(self.subgroup_item_freq[subgroup].values())

        assert len(its) == len(self.content_freq)
        print 'total item number:', len(self.content_freq)
        print 'total bottom subgroup number:', len(self.subgroup_item_freq)

    def calculate_global_pop(self):
        filename = dir + str(len(self.content_freq))+' glb_pop.cp'
        if not os.path.exists(filename):
            self.global_pop = copy.deepcopy(self.subgroup_item_freq)
            # normalize to (0,1.)
            for subgroup in self.global_pop:
                sum_v = sum(self.global_pop[subgroup].values())
                for item in self.global_pop[subgroup]:
                    self.global_pop[subgroup][item] /= 1.*sum_v
            with open(filename,'wb') as outfile:
                cp.dump(self.global_pop,outfile)
        else:
            with open(filename,'rb') as infile:
                self.global_pop = cp.load(infile)

    def calculate_MF_pop(self):
        filename = dir + str(len(self.content_freq)) + "_" + str(len(self.subgroup_item_freq)) \
                   + ' mf_pop.cp'
        if not os.path.exists(filename):
            # generate id for subgroups and contents
            subgroup_id = {}
            content_id = {}
            subgroup_cnt = 0
            content_cnt = 0
            for subgroup in self.subgroup_item_freq:
                subgroup_id[subgroup] = subgroup_cnt
                subgroup_cnt += 1
                for content in self.subgroup_item_freq[subgroup]:
                    if content not in content_id:
                        content_id[content] = content_cnt
                        content_cnt += 1

            # generate rating matrix, entries normalized
            print '---preparing rating matrix...'
            rating_mat = []
            for subgroup in self.subgroup_item_freq:
                uid = subgroup_id[subgroup]
                for content in self.subgroup_item_freq[subgroup]:
                    cid = content_id[content]
                    rate = self.subgroup_item_freq[subgroup][content]*1./self.arrival_rate[subgroup]
                    rating_mat.append([uid,cid,rate])

            # MF
            row = []
            col = []
            data = []
            X = np.array(rating_mat)
            n_user = int(max(X[:, 0])) + 1
            n_item = int(max(X[:, 1])) + 1
            for r in rating_mat:
                row.append(int(r[0]))
                col.append(int(r[1]))
                data.append(r[2])

            spMatrix = csr_matrix((data, (row, col)), shape=(n_user, n_item))
            print '------shape of rating matrix:', spMatrix.shape
            model = NMF(n_components=COMPONENT,
                        init='random',
                        random_state=0)
            print '---factorizing rating matrix...'
            model.fit(spMatrix)
            user_component = model.transform(spMatrix)
            component_item = model.components_

            id_content = dict((v, k) for k, v in content_id.iteritems())
            items = []
            for i in range(n_item):
                items.append(id_content[i])

            for subgroup in subgroup_id:
                uid = subgroup_id[subgroup]
                r_u = list(np.dot(user_component[uid], component_item)) # rating vector for user u
                self.MF_pop[subgroup] = dict(zip(items, r_u))

            with open(filename,'wb') as outfile:
                cp.dump(self.MF_pop,outfile)

        else:
            with open(filename,'rb') as infile:
                self.MF_pop = cp.load(infile)



