import networkx as nx

class policy_evaluator(object):
    def __init__(self, reqlist_test, root,lv3graph, UP_LEVEL_PREFIX,
                 d_b = 5., d_h_mid = 5.5, d_h_up = 11., d_m_mid = 30.5, d_m_up = 61,
                 LRU_prob = .7):
        self.sum_delay = 0.
        self.reqlist_test = \
            [req for req in reqlist_test if req[1][:UP_LEVEL_PREFIX]==root] # [time,ip,content]
        self.level3graph = lv3graph

        self.d_b = d_b
        self.d_h_mid = d_h_mid
        self.d_h_up = d_h_up
        self.d_m_mid = d_m_mid
        self.d_m_up = d_m_up
        self.LRU_prob = LRU_prob

        self.cnt_new = 0
        self.cnt_d_b = 0
        self.cnt_d_h_mid = 0
        self.cnt_d_h_up = 0
        self.cnt_d_m_mid = 0
        self.cnt_d_m_up = 0

        self.cnt_list = []


    def evaluate(self, pLRU = False, static_caching = True, MFLRU = False):
        def calculate_delay(placement_policy,routing_policy):
            print 'evaluating delay...'
            self.sum_delay = 0. # reset sum delay
            for req in self.reqlist_test:
                source_ip = req[1][:self.level3graph.BOTTOM_LEVEL_PREFIX]
                req_content = req[2]

                if source_ip not in routing_policy.keys(): # new ip ignored...
                    continue

                if req_content not in routing_policy[source_ip].keys(): # new content, use uncached path...
                    self.sum_delay += self.d_b
                    self.cnt_d_b += 1
                    self.cnt_new += 1
                    continue

                dest_ip = routing_policy[source_ip][req_content]
                # if no path between source and dest, delay = d_b
                if not nx.has_path(self.level3graph.graph, source_ip[:self.level3graph.MID_LEVEL_PREFIX], dest_ip):
                    self.sum_delay += self.d_b
                    self.cnt_d_b += 1
                else:
                    # if path exist but no content stored
                    if req_content not in placement_policy[dest_ip]:
                        if dest_ip in self.level3graph.mid_nodes:
                            self.sum_delay += self.d_m_mid
                            self.cnt_d_m_mid += 1
                        elif dest_ip in self.level3graph.up_nodes:
                            self.sum_delay += self.d_m_up
                            self.cnt_d_m_up += 1
                        else:
                            print 'dest ip not in graph nodes !'
                            assert True
                    else:
                        if dest_ip in self.level3graph.mid_nodes:
                            self.sum_delay += self.d_h_mid
                            self.cnt_d_h_mid += 1
                        elif dest_ip in self.level3graph.up_nodes:
                            self.sum_delay += self.d_h_up
                            self.cnt_d_h_up += 1
                        else:
                            print 'dest ip not in graph nodes !'
                            assert True
            return self.cnt_new,self.cnt_d_b,self.cnt_d_h_mid,self.cnt_d_h_up,\
                   self.cnt_d_m_mid,self.cnt_d_m_up,self.sum_delay

        if static_caching:
            print '-'*80
            print 'printing results for global placement&routing...'
            glb_placement = self.level3graph.global_placement
            glb_routing = self.level3graph.global_routing
            glb_delay = calculate_delay(glb_placement,glb_routing)
            self.print_perf()
            self.cnt_list.append([self.cnt_d_b,self.cnt_d_h_mid,self.cnt_d_h_up])

            self.cnt_new = 0
            self.cnt_d_b = 0  # reset counts...
            self.cnt_d_h_mid = 0
            self.cnt_d_h_up = 0
            self.cnt_d_m_mid = 0
            self.cnt_d_m_up = 0

            print 'printing results for MF placement&routing...'
            mf_placement = self.level3graph.mf_placement
            mf_routing = self.level3graph.mf_routing
            mf_delay = calculate_delay(mf_placement, mf_routing)
            self.print_perf()

            prev_mid = self.cnt_list[0][1]
            multi = self.cnt_d_h_mid*1./prev_mid
            self.cnt_d_h_up = int(self.cnt_list[0][2] * multi)
            self.cnt_d_b = sum(self.cnt_list[0])-self.cnt_d_h_mid-self.cnt_d_h_up
            self.cnt_list.append([self.cnt_d_b, self.cnt_d_h_mid, self.cnt_d_h_up])

            print 'print differences between glob & mf caching and routing...'
            self.print_diff(glb_placement,glb_routing,mf_placement,mf_routing)


        if MFLRU:
            self.sum_delay = 0.
            reqlist_pass = []
            for req in self.reqlist_test:
                req_content = req[2]
                pass_item = self.level3graph.update_MFLRU(req_content,self.level3graph.mid_nodes)
                if pass_item:
                    reqlist_pass.append(pass_item)
                else:
                    self.sum_delay += self.d_h_mid
                    self.cnt_d_h_mid += 1

            for item in reqlist_pass:
                pass_item = self.level3graph.update_MFLRU(item,self.level3graph.up_nodes)
                if pass_item:
                    self.sum_delay += self.d_b
                    self.cnt_d_b += 1
                else:
                    self.sum_delay += self.d_h_up
                    self.cnt_d_h_up += 1

            print 'printing results for MFLRU...'
            self.print_perf()


        if pLRU:
            i = 0 # to do

        return

    def print_perf(self):
        print 'd_b=',self.d_b,' d_h_mid=',self.d_h_mid,' d_h_up=',self.d_h_up,' d_m_mid=',self.d_m_mid,' d_m_up=',self.d_m_up
#        print ' level2_Cm=',self.level3graph.level2_Cm,' level1_Cm=',self.level3graph.level1_Cm
#        print 'linkcost_same=',self.level3graph.linkcost_same
        print 'number of unique files:', len(self.level3graph.popularities.content_freq)
        total_cap = self.level3graph.level2_Cm*len(self.level3graph.mid_nodes)\
                    +self.level3graph.level1_Cm*len(self.level3graph.up_nodes)
        print 'total cache capacity:', total_cap
        print 'cache_catalog_percent:',total_cap*1./len(self.level3graph.popularities.content_freq)
        print 'count db,dh_mid,dh_up,dm_mid,dm_up:',self.cnt_d_b,self.cnt_d_h_mid,self.cnt_d_h_up,self.cnt_d_m_mid,self.cnt_d_m_up
        print 'sum delay=', self.sum_delay
        print '-'*80

    def print_diff(self,glb_placement,glb_routing,mf_placement,mf_routing):
        print 'difference between caching:'
        cache_diff = 0
        for cache in glb_placement:
            cache_diff += len(glb_placement[cache]&mf_placement[cache])
        print cache_diff,'items.'
        print 'difference between routing:'
        rout_diff = 0
        for subgroup in mf_routing:
            for content in mf_routing[subgroup]:
                if content not in glb_routing[subgroup]:
                    rout_diff += 1
                elif mf_routing[subgroup] != glb_routing[subgroup]:
                    rout_diff += 1
        print rout_diff,'routs.'





