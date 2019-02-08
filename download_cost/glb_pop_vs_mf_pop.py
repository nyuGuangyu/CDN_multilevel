import cPickle as cp
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from operator import itemgetter
import random


filename = 'mf_pop.cp'
filename1 = 'glb_pop.cp'
with open(filename,'rb') as infile, open(filename1) as infile1:
    mf_pop = cp.load(infile)
    glb_pop = cp.load(infile1)

random_user = random.choice(mf_pop.keys())
mf_entries = dict(zip(range(1,len(mf_pop[random_user])+1),[ele[1] for ele in sorted(mf_pop[random_user].items(),key=itemgetter(1),reverse=True)]))
for item in mf_pop[random_user].keys():
    if item not in glb_pop[random_user]:
        glb_pop[random_user][item] = 0
glb_entries = dict(zip(range(1,len(glb_pop[random_user])+1),[ele[1] for ele in sorted(glb_pop[random_user].items(),key=itemgetter(1),reverse=True)]))


f = plt.figure()
ax = f.add_subplot(111)    # The big subplot
ax1 = f.add_subplot(211)
ax2 = f.add_subplot(212)

# Turn off axis lines and ticks of the big subplot
ax.spines['top'].set_color('none')
ax.spines['bottom'].set_color('none')
ax.spines['left'].set_color('none')
ax.spines['right'].set_color('none')
ax.tick_params(labelcolor='w', top='off', bottom='off', left='off', right='off')

ax1.bar(list(glb_entries.keys()), glb_entries.values(), color='g')
ax2.bar(list(mf_entries.keys()), mf_entries.values(), color='r')

# Set common labels
ax.set_ylabel('File Popularities')
ax.set_xlabel('File Popularity Ranks')

ax1.set_title('Global Pop')
ax2.set_title('MF-generated Pop')

# f.savefig("mf_vs_glb.pdf", bbox_inches='tight')
f.savefig("mf_vs_glb.pdf")


