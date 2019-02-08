import networkx as nx
import os
import cPickle as cp
from collections import defaultdict
import operator
import sys
import random

dir = '/home/lgy/CDN_multilevel/code/optimal_results/'

class level3_graph(object): # feed popularity
    """
    Using IP appearance from data create 3 level graph with attribute: S,X,Xm,D according to paper.
    level1 node: prefix 16;
    level2 node: prefix 18;
    level3 node: prefix 20.
    
    level 3 nodes have no connections among themselves;
    level 2 nodes have connections...;
    level 1 nodes have connections.
    
    There is no root cache server for storing the whole catalog. Instead we use the "unached path" according to paper.
    
    Each node have attributes: Cm,Sm
    """
    def __init__(self, popularities, cache_catalog_percent, root, level_factor = 1, linkcost_same = 1.,
                 d_b = 5., d_h_mid=5.5, d_h_up = 11., d_m_mid = 30.5, d_m_up = 61,
                 BOTTOM_LEVEL_PREFIX = 20, MID_LEVEL_PREFIX = 18, UP_LEVEL_PREFIX = 16):
        self.graph = nx.Graph()
        self.graph_attr = dict()
        self.node_attr = defaultdict(dict)
        self.popularities = popularities
        self.target_up_level_ip = root

        self.cache_catalog_percent = cache_catalog_percent
        self.level2_Cm = int(len(self.popularities.content_freq)*cache_catalog_percent/5.)
        self.level1_Cm = level_factor * self.level2_Cm # 5 caches in total, up level size=level_factor*mid level
        self.d_b = d_b
        self.d_h_mid = d_h_mid
        self.d_h_up = d_h_up
        self.d_m_mid = d_m_mid
        self.d_m_up = d_m_up
        self.BOTTOM_LEVEL_PREFIX = BOTTOM_LEVEL_PREFIX
        self.MID_LEVEL_PREFIX = MID_LEVEL_PREFIX
        self.UP_LEVEL_PREFIX = UP_LEVEL_PREFIX
        self.linkcost_same = linkcost_same


        self.global_placement = defaultdict(list)
        self.global_routing = defaultdict(lambda:defaultdict(dict)) # 3-d dict to store p[i][j][m]

        self.mf_placement = defaultdict(list)
        self.mf_routing = defaultdict(lambda:defaultdict(dict))  # 3-d dict to store p[i][j][m]

        self.MFLRU_initial_placement = defaultdict(list)
        self.LRU_initial_placement = defaultdict(list)

        # create 3 level nodes
        print 'Creating nodes for lv3graph...'

        def __get_extension(upper,lower):
            ext = []
            num = (lower-upper)*2
            for i in range(num):
                e = bin(i)[2:]
                if len(e) < lower-upper:
                    e = '0'*(lower-upper-len(e)) + e
                ext.append(e)
            return  ext

        self.up_nodes = [self.target_up_level_ip]
        self.graph.add_node(self.target_up_level_ip)
        self.node_attr[self.target_up_level_ip]['Cm'] = self.level1_Cm
        self.node_attr[self.target_up_level_ip]['Xm'] = set()

        self.mid_nodes = []
        for node in self.up_nodes:
            for ext in __get_extension(self.UP_LEVEL_PREFIX,self.MID_LEVEL_PREFIX):
                self.mid_nodes.append(node+ext)
                self.graph.add_node(node+ext)
                self.node_attr[node+ext]['Cm'] = self.level2_Cm
                self.node_attr[node+ext]['Xm'] = set()

        self.bottom_nodes = []
        for node in self.mid_nodes:
            for ext in __get_extension(self.MID_LEVEL_PREFIX,self.BOTTOM_LEVEL_PREFIX):
                self.bottom_nodes.append(node+ext)
                self.graph.add_node(node+ext)

        # create cross-level connections
        print 'Creating edges for lv3graph...'
        for ip in self.bottom_nodes:
            upper_ip = ip[:MID_LEVEL_PREFIX]
            if upper_ip in self.mid_nodes:
                self.graph.add_edge(ip,upper_ip,weight=linkcost_same)
        for ip in self.mid_nodes:
            upper_ip = ip[:UP_LEVEL_PREFIX]
            if upper_ip in self.up_nodes:
                self.graph.add_edge(ip,upper_ip,weight=linkcost_same)

        # create in-level connections: ignored for now ...

    def update_static_placement_routing(self):
        arrival_rate = self.popularities.arrival_rate # {subgroup : req nb}
        global_probs = self.popularities.global_pop # 2d dict
        MF_probs = self.popularities.MF_pop

        # indexing the strings! may be slow for long string lookup in dicts
        subgroups = [sub for sub in self.popularities.subgroup_item_freq.keys()
                     if sub[:self.UP_LEVEL_PREFIX]==self.target_up_level_ip] # only keep the subgroup under this subtress
        sid_subgroup = dict(zip(range(len(subgroups)),subgroups))
        subgroup_sid = dict((v, k) for k, v in sid_subgroup.iteritems())

        contents = self.popularities.content_freq.keys() # list
        cid_content = dict(zip(range(len(contents)), contents))
        content_cid = dict((v, k) for k, v in cid_content.iteritems())

        caches = self.mid_nodes + self.up_nodes # list
        mid_cache = dict(zip(range(len(caches)), caches))
        cache_mid = dict((v, k) for k, v in mid_cache.iteritems())

        print 'number of up caches=',len(self.up_nodes)
        print 'number of mid caches=', len(self.mid_nodes)

        # greedy appox. without perf guarantees
        def greedy_placement(arrival_rate,q_ij):
            q = defaultdict(dict)
            lamda_i = {}
            for subgroup in q_ij:
                if subgroup not in subgroup_sid: # only keep the subgroup under this subtress + indexing
                    continue
                for content in q_ij[subgroup]:
                    q[subgroup_sid[subgroup]][content_cid[content]] = q_ij[subgroup][content]
            for subgroup in arrival_rate:
                if subgroup not in subgroup_sid:
                    continue
                lamda_i[subgroup_sid[subgroup]] = arrival_rate[subgroup]

            # reset dictionaries...
            self.graph_attr['X'] = defaultdict(list) # Xjm
            self.graph_attr['P'] = defaultdict(dict) # Pijm
            for mid,cache in enumerate(caches):
                self.node_attr[mid]['Xm'] = set()
                self.node_attr[mid]['Cm'] = self.node_attr[cache]['Cm']

            # d = defaultdict(dict)  # 2-d dict d_ij
            # for sid,subgroup in enumerate(subgroups):
            #     for cid,content in enumerate(contents):
            #         d[sid][cid] = self.d_m_mid # regarding the tree topo, modify when use other topo.

            # placement
            total_capacity = 0
            for mid,cache in enumerate(caches):
                total_capacity += self.node_attr[mid]['Cm']
            print 'Total cache capacity=', total_capacity

            def iterate_level(arrival_rate_index,q_ij_index,cache_ids):
                _q = q_ij_index  # 2-d dict
                _lamda_i = arrival_rate_index
                _subgroups = arrival_rate_index.keys()

                S = {}
                string_len = len(cache_ids[0])
                for m in range(len(cache_ids)):
                    if len(cache_ids[m]) != string_len:
                        print 'mixed level of caches!!'
                        sys.exit()
                    if m not in S:
                        S[m] = set()
                    for j in range(len(contents)):
                        S[m].add(j)

                _d = defaultdict(dict)
                for sid, subgroup in enumerate(_subgroups):
                    for cid, content in enumerate(contents):
                        if len(cache_ids[0]) == self.MID_LEVEL_PREFIX:
                            _d[sid][cid] = self.d_m_mid
                        else:
                            _d[sid][cid] = self.d_h_up - self.d_h_mid

                while S:
                    print zip(S.keys(),[len(S[x]) for x in S.keys()])
                    G = {}
                    for mid in S.keys():
                        for cid in S[mid]:
                            sum_gain = 0.
                            for sid in range(len(_subgroups)):
                                if len(cache_ids[mid]) == self.MID_LEVEL_PREFIX \
                                        and sid_subgroup[sid][:self.MID_LEVEL_PREFIX] == cache_ids[mid] \
                                        and cid in _q[sid] and sid in _lamda_i:
                                    if _d[sid][cid] >= self.d_h_mid:
                                        sum_gain += _lamda_i[sid] * _q[sid][cid] * (
                                            _d[sid][cid] - self.d_h_mid)

                                elif len(cache_ids[mid]) == self.UP_LEVEL_PREFIX \
                                        and sid_subgroup[sid][:self.UP_LEVEL_PREFIX] == cache_ids[mid] \
                                        and cid in _q[sid] and sid in _lamda_i:
                                    if _d[sid][cid] >= self.d_h_up - self.d_h_mid:
                                        sum_gain += _lamda_i[sid] * _q[sid][cid] * (
                                            _d[sid][cid] - (self.d_h_up - self.d_h_mid))
                            G[(mid,cid)] = sum_gain

                    m_star,j_star = max(G.iteritems(), key=operator.itemgetter(1))[0]

                    true_id = cache_mid[cache_ids[m_star]]
                    self.node_attr[true_id]['Xm'].add(j_star)
                    if len(self.node_attr[true_id]['Xm']) == self.node_attr[true_id]['Cm']:
                        S.pop(m_star)
                        print 'removing cache:',m_star,"left cache:", S.keys()

                    if j_star in self.graph_attr['X'][true_id]:
                        print 'existing item:',m_star,j_star
                    else:
                        self.graph_attr['X'][true_id].append(j_star)
                        if m_star in S:
                            S[m_star] -= {j_star}

                for sid,subgroup in enumerate(_subgroups):
                    if cache_ids[m_star] in self.mid_nodes:
                        _d[sid][j_star] = min(_d[sid][j_star], self.d_h_mid)
                    elif cache_ids[m_star] in self.up_nodes:
                        _d[sid][j_star] = min(_d[sid][j_star], (self.d_h_up - self.d_h_mid))


            # *********iterate algo level by level ************
            # update mid level caches....
            iterate_level(lamda_i,q,self.mid_nodes)

            print 'lamda_i before filter========'
            print lamda_i

            # generate up level lamda_i_up, q_up. No need to change keys in lamda_i ! We just assume subgroups directly connect to upper cache!
            print 'filtering request to the upper caches...'
            for i in lamda_i:
                subgroup = sid_subgroup[i]
                connected_cache_id = cache_mid[subgroup[:self.MID_LEVEL_PREFIX]]
                for j in q[i].keys():
                    if j in self.graph_attr['X'][connected_cache_id]:
                        lamda_i[i] -= int(lamda_i[i]*q[i][j])
                        q[i].pop(j)

            print 'lamda_i after filter========'
            print lamda_i

            # pass new lamda_i,q up to next level
            iterate_level(lamda_i, q, self.up_nodes)

            # greedily find optimal routing, remove indices...
            for sid,subgroup in enumerate(subgroups):
                for cid,content in enumerate(contents):
                    if cid in self.node_attr[cache_mid[subgroup[:self.MID_LEVEL_PREFIX]]]['Xm']:
                        self.graph_attr['P'][subgroup][content] = subgroup[:self.MID_LEVEL_PREFIX]
                    elif cid in self.node_attr[cache_mid[subgroup[:self.UP_LEVEL_PREFIX]]]['Xm']:
                        self.graph_attr['P'][subgroup][content] = subgroup[:self.UP_LEVEL_PREFIX]
            # remove indices on X
            for mid,cache in enumerate(caches):
                name_set = set()
                for cid in self.graph_attr['X'][mid]:
                    name_set.add(cid_content[cid])
                self.graph_attr["X"][cache] = name_set
                del self.graph_attr['X'][mid]

            return self.graph_attr['X'], self.graph_attr['P']

        print 'Updating static placement&routing for global Pop...'
        filename1 = dir + str(len(contents)) + '_' + str(self.cache_catalog_percent) + ' glb_placement.cp'
        filename2 = dir + str(len(contents)) + '_' + str(self.cache_catalog_percent) + ' glb_routing.cp'
        if not (os.path.exists(filename1) and os.path.exists(filename2)):
            self.global_placement,self.global_routing = greedy_placement(arrival_rate,global_probs)
            with open(filename1,'wb') as outfile1, open(filename2,'wb') as outfile2:
                cp.dump(self.global_placement,outfile1)
                cp.dump(self.global_routing,outfile2)
        elif os.path.exists(filename1) and os.path.exists(filename2):
            with open(filename1,'rb') as infile1, open(filename2,'rb') as infile2:
                self.global_placement = cp.load(infile1)
                self.global_routing = cp.load(infile2)

        print 'Updating static placement&routing for MF Pop...'
        filename1 = dir + str(len(contents)) + "_" + str(len(subgroups)) + '_' + str(self.cache_catalog_percent) \
                   + ' mf_placement.cp'
        filename2 = dir + str(len(contents)) + "_" + str(len(subgroups)) + '_' + str(self.cache_catalog_percent) \
                   + ' mf_routing.cp'
        if not (os.path.exists(filename1) and os.path.exists(filename2)):
            self.mf_placement,self.mf_routing = greedy_placement(arrival_rate,MF_probs)
            with open(filename1,'wb') as outfile1, open(filename2,'wb') as outfile2:
                cp.dump(self.mf_placement, outfile1)
                cp.dump(self.mf_routing, outfile2)
        elif os.path.exists(filename1) and os.path.exists(filename2):
            with open(filename1,'rb') as infile1, open(filename2,'rb') as infile2:
                self.mf_placement = cp.load(infile1)
                self.mf_routing = cp.load(infile2)


    def get_initial_MFLRU_placement(self,train,propotion = 0.6):
        reqlist_train = [req for req in train if req[1][:self.UP_LEVEL_PREFIX]==self.target_up_level_ip]
        subgroups = [sub for sub in self.popularities.subgroup_item_freq.keys()
                     if sub[
                        :self.UP_LEVEL_PREFIX] == self.target_up_level_ip]  # only keep the subgroup under this subtress
        contents = self.popularities.content_freq.keys()  # list
        caches = self.mid_nodes + self.up_nodes

        filename = dir + str(len(contents)) + "_" + str(len(subgroups)) + '_' + str(self.cache_catalog_percent) \
                    + ' mf_placement.cp'
        if not (os.path.exists(filename)):
            self.update_static_placement_routing()
        else:
            if not self.mf_placement:
                with open(filename,'rb') as infile:
                    self.mf_placement = cp.load(infile)
            # first fill mf part to each cache
            for node in caches:
                self.MFLRU_initial_placement[node] = {}
                mf_length = int(self.node_attr[node]['Cm'] * propotion)
                mf_part = list(self.mf_placement[node])[:mf_length]
                self.MFLRU_initial_placement[node]['mf'] = mf_part
                self.MFLRU_initial_placement[node]['lru'] = list()

            # then let reqlist fill LRU part
            reqlist_pass = []
            for [time,ip,item] in reqlist_train:
                pass_item= self.update_MFLRU(item,self.mid_nodes)
                if pass_item:
                    reqlist_pass.append(pass_item)

            for item in reqlist_pass:
                self.update_MFLRU(item,self.up_nodes)

        for cache in self.MFLRU_initial_placement:
            print cache,':','mf:',len(self.MFLRU_initial_placement[cache]['mf']),\
                ' lru:',len(self.MFLRU_initial_placement[cache]['lru'])

    def update_MFLRU(self,item,caches):
        rnd = random.randint(0, len(caches)-1)  # randomly choose one cache
        target_cache = caches[rnd]
        if item not in self.MFLRU_initial_placement[target_cache]['mf']:
            if len(self.MFLRU_initial_placement[target_cache]['lru']) \
                    < self.node_attr[target_cache]['Cm'] \
                    - len(self.MFLRU_initial_placement[target_cache]['lru']):
                if item not in self.MFLRU_initial_placement[target_cache]['lru']:
                    self.MFLRU_initial_placement[target_cache]['lru'].append(item)
                    return item
            elif item not in self.MFLRU_initial_placement[target_cache]['lru']:
                self.MFLRU_initial_placement[target_cache]['lru'].pop(0)
                self.MFLRU_initial_placement[target_cache]['lru'].append(item)
                return item

        return None

    def get_initial_LRU_placement(self):

        return

    def update_LRU(self):

        return

