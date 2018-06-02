from krrt.utils import get_opts
from krrt.sat.CNF import OptimizedLevelWeightedFormula

import math

def readBNN(directory):
    
    layers = []
    weights = {}
    BNNFile = open(directory,"r")
    data = BNNFile.read().splitlines()
    
    layerSizeIndex = 1
    input = 0
    output = 0
    layer = 0
    out = 0
    
    for index, dat in enumerate(data):
        if (index == layerSizeIndex):
            input, output = dat.split(",")
            layerSizeIndex = int(output) + layerSizeIndex + 1
            layers.append([int(input),int(output)])
            layer += 1
            out = 0
        else:
            for inp in range(int(input)):
                weight = 0
                if (dat[int(inp)] == '0'):
                    weight = -1
                elif (dat[int(inp)] == '1'):
                    weight = 1
                else:
                    weight = 0
                weights[(layer-1, inp, out)] = weight
            out += 1

    return weights, layers

def readNormalization(directory, layers):
    
    nLayers = len(layers)
    normalization = []
    NormalizationFile = open(directory,"r")
    data = NormalizationFile.read().splitlines()
    
    for index, dat in enumerate(data):
        if index > 0:
            normalization.append(dat.split(","))

    return normalization

def encode_hd_maxsat_plan(domain, instance, horizon):
    
    weights, layers = readBNN("./bnn_"+domain+"_"+instance+".txt")
    normalization = readNormalization("./normalization_"+domain+"_"+instance+".txt", layers)
    nHiddenLayers = len(layers)-1
    literals = []
    VARINDEX = 1
    
    A = []
    S = []
    SPrime = []
    
    #navigation
    if domain == "navigation" and instance == "3x3":
        A = ['move-east', 'move-north', 'move-south', 'move-west']
        S = ['robot-at[$x21| $y12]', 'robot-at[$x21| $y15]', 'robot-at[$x21| $y20]', 'robot-at[$x14| $y12]', 'robot-at[$x14| $y15]', 'robot-at[$x14| $y20]', 'robot-at[$x9| $y12]', 'robot-at[$x9| $y15]', 'robot-at[$x9| $y20]']
        SPrime = S
    elif domain == "navigation" and instance == "4x3":
        A = ['move-east', 'move-north', 'move-south', 'move-west']
        S = ['robot-at[$x21| $y12]', 'robot-at[$x21| $y15]', 'robot-at[$x21| $y20]', 'robot-at[$x14| $y12]', 'robot-at[$x14| $y15]', 'robot-at[$x14| $y20]', 'robot-at[$x9| $y12]', 'robot-at[$x9| $y15]', 'robot-at[$x9| $y20]', 'robot-at[$x6| $y12]', 'robot-at[$x6| $y15]', 'robot-at[$x6| $y20]']
        SPrime = S

    formula = OptimizedLevelWeightedFormula()

    # Create vars for each action a, time step t
    x = {}
    nameX = {}
    for a in A:
        for t in range(horizon):
            x[(a,t)] = VARINDEX
            nameX[VARINDEX] = (a,t)
            VARINDEX += 1

    # Create vars for each state a, time step t
    y = {}
    nameY = {}
    for s in S:
        for t in range(horizon+1):
            y[(s,t)] = VARINDEX
            nameY[VARINDEX] = (s,t)
            VARINDEX += 1

    # Create vars for each activation node z at depth d, width w, time step t
    z = {}
    nameZ = {}
    for t in range(horizon):
        for d in range(nHiddenLayers):
            for w in range(layers[d][1]):
                z[(d,w,t)] = VARINDEX
                nameZ[VARINDEX] = (d,w,t)
                VARINDEX += 1

    # Hard clauses

    if domain == "navigation":
        # Set mutual exclusion on actions
        for t in range(horizon):
            actionLiterals = []
            for a in A:
                actionLiterals.append(x[(a,t)])
            VARINDEX, formula = addAtMostKSeq(actionLiterals, 1, formula, VARINDEX)

    # Set initial state
    for s in S:
        if domain == "navigation" and instance == "3x3" and s == 'robot-at[$x14| $y20]':
            formula.addClause([y[(s,0)]])
        elif domain == "navigation" and instance == "4x3" and  s == 'robot-at[$x14| $y12]':
            formula.addClause([y[(s,0)]])
        else:
            formula.addClause([-y[(s,0)]])

    # Set goal state
    for s in S:
        if domain == "navigation" and instance == "3x3" and s == 'robot-at[$x14| $y12]':
            formula.addClause([y[(s,horizon)]])
        elif domain == "navigation" and instance == "4x3" and s == 'robot-at[$x14| $y20]':
            formula.addClause([y[(s,horizon)]])
        else:
            formula.addClause([-y[(s,horizon)]])

    # Set node activations
    for t in range(horizon):
        for d in range(nHiddenLayers):
            for out in range(layers[d][1]):
                positiveInputLiterals = []
                
                layersize = 0
                
                if d == 0: # input is state or actions
                    for inp, a in enumerate(A):
                        if weights[(d, inp, out)] > 0:
                            positiveInputLiterals.append(x[(a,t)])
                            layersize += 1
                        elif weights[(d, inp, out)] < 0:
                            positiveInputLiterals.append(-x[(a,t)])
                            layersize += 1
                    for i, s in enumerate(S):
                        inp = i + len(A)
                        if weights[(d, inp, out)] > 0:
                            positiveInputLiterals.append(y[(s,t)])
                            layersize += 1
                        elif weights[(d, inp, out)] < 0:
                            positiveInputLiterals.append(-y[(s,t)])
                            layersize += 1
                else:
                    for inp in range(layers[d][0]):
                        if weights[(d, inp, out)] > 0:
                            positiveInputLiterals.append(z[(d-1,inp,t)])
                            layersize += 1
                        elif weights[(d, inp, out)] < 0:
                            positiveInputLiterals.append(-z[(d-1,inp,t)])
                            layersize += 1
            
                positive_threshold = int(math.ceil(layersize/2.0 + float(normalization[d][out])/2.0))
                negative_threshold = layersize - positive_threshold + 1
                
                if positive_threshold >= layersize + 1:
                    formula.addClause([-z[(d,out,t)]])
                elif negative_threshold >= layersize + 1:
                    formula.addClause([z[(d,out,t)]])
                else:
                    if positive_threshold < negative_threshold:
                        VARINDEX, formula = addCardNetworkBinaryActivation(positiveInputLiterals, positive_threshold, formula, VARINDEX, z[(d,out,t)])
                        #VARINDEX, literals = addBinaryActivationSeq(positiveInputLiterals, positive_threshold, literals, VARINDEX, z[(d,out,t)])
                        #VARINDEX, literals = addAtLeastBinaryActivationPar(positiveInputLiterals, positive_threshold, literals, VARINDEX, z[(d,out,t)])
                        #VARINDEX, literals = addAtLeastBinaryActivationPar(negativeInputLiterals, negative_threshold, literals, VARINDEX, -z[(d,out,t)])
                    else:
                        negativeInputLiterals = [-i for i in positiveInputLiterals]
                        VARINDEX, formula = addCardNetworkBinaryActivation(negativeInputLiterals, negative_threshold, formula, VARINDEX, -z[(d,out,t)])

    # Set next state
    for t in range(horizon):
        d = nHiddenLayers
        for out, s in enumerate(SPrime):
            positiveInputLiterals = []
            
            layersize = 0
            
            for inp in range(layers[d][0]):
                if weights[(d, inp, out)] > 0:
                    positiveInputLiterals.append(z[(d-1,inp,t)])
                    layersize += 1
                elif weights[(d, inp, out)] < 0:
                    positiveInputLiterals.append(-z[(d-1,inp,t)])
                    layersize += 1
        
            positive_threshold = int(math.ceil(layersize/2.0 + float(normalization[d][out])/2.0))
            negative_threshold = layersize - positive_threshold + 1
            
            if positive_threshold >= layersize + 1:
                literals.append([-y[(s,t+1)]])
            elif negative_threshold >= layersize + 1:
                literals.append([y[(s,t+1)]])
            else:
                if positive_threshold < negative_threshold:
                    VARINDEX, formula = addCardNetworkBinaryActivation(positiveInputLiterals, positive_threshold, formula, VARINDEX, y[(s,t+1)])
                    #VARINDEX, literals = addBinaryActivationSeq(positiveInputLiterals, positive_threshold, literals, VARINDEX, y[(s,t+1)])
                    #VARINDEX, literals = addAtLeastBinaryActivationPar(positiveInputLiterals, positive_threshold, literals, VARINDEX, y[(s,t+1)])
                    #VARINDEX, literals = addAtLeastBinaryActivationPar(negativeInputLiterals, negative_threshold, literals, VARINDEX, -y[(s,t+1)])
                else:
                    negativeInputLiterals = [-i for i in positiveInputLiterals]
                    VARINDEX, formula = addCardNetworkBinaryActivation(negativeInputLiterals, negative_threshold, formula, VARINDEX, -y[(s,t+1)])

    formula.writeCNF(domain+str(horizon)+'.wcnf')
    formula.writeCNF(domain+str(horizon)+'.cnf', hard=True)
    
    print ''
    print "Vars: %d" % formula.num_vars
    print "Clauses: %d" % formula.num_clauses
    #print "Soft: %d" % len(formula.getSoftClauses())
    print "Hard: %d" % len(formula.getHardClauses())
    print "Max Weight: %d" % formula.top_weight
    print ''

def addAtMostKSeq(x, k, formula, VARINDEX): # Sinz (2005 encoding)
    
    n = len(x)
    
    # Create the vars for  partial sum bits
    s = {}
    for i in range(n):
        for j in range(k):
            s[(i,j)] = VARINDEX
            VARINDEX += 1

    formula.addClause([-x[(0)], s[(0,0)]])
    
    for j in range(1,k):
        formula.addClause([-s[(0,j)]])

    for i in range(1,n-1):
        formula.addClause([-x[(i)], s[(i,0)]])
        formula.addClause([-s[(i-1,0)], s[(i,0)]])
        
        for j in range(1,k):
            formula.addClause([-x[(i)], -s[(i-1,j-1)], s[(i,j)]])
            formula.addClause([-s[(i-1,j)], s[(i,j)]])
        
        formula.addClause([-x[(i)], -s[(i-1,k-1)]])

    formula.addClause([-x[(n-1)], -s[(n-2,k-1)]])
    
    return VARINDEX, formula

def hMerge(a, b, k, formula, VARINDEX):
    
    n = len(a)
    
    # Create the vars for output bits
    c = []
    for i in range(2*n):
        c.append(VARINDEX)
        VARINDEX += 1
    
    if n == 1:
        formula.addClause([a[(0)], b[(0)], -c[(0)]])
        formula.addClause([a[(0)], -c[(1)]])
        formula.addClause([b[(0)], -c[(1)]])
        
        # new
        formula.addClause([-a[(0)], c[(0)]])
        formula.addClause([-b[(0)], c[(0)]])
        formula.addClause([c[(1)], -a[(0)], -b[(0)]])
    
    elif n > 1:
        a_even = a[1::2]
        b_even = b[1::2]
        a_odd = a[::2]
        b_odd = b[::2]
        
        d, VARINDEX, formula = hMerge(a_odd, b_odd, k, formula, VARINDEX)
        e, VARINDEX, formula = hMerge(a_even, b_even, k, formula, VARINDEX)
        
        for i in range(n-1):
            formula.addClause([d[(i+1)], e[(i)], -c[(2*i + 1)]])
            formula.addClause([d[(i+1)], -c[(2*i+1 + 1)]])
            formula.addClause([e[(i)], -c[(2*i+1 + 1)]])
            
            #new
            formula.addClause([-d[(i+1)], c[(2*i + 1)]])
            formula.addClause([-e[(i)], c[(2*i + 1)]])
            formula.addClause([-e[(i)], -d[(i+1)], c[(2*i+1 + 1)]])
        
        c = [d[0]] + c[1:-1] + [e[len(e)-1]]
    
    return c, VARINDEX, formula

def sMerge(a, b, k, formula, VARINDEX):
    
    n = len(a)
    
    # Create the vars for output bits
    c = []
    for i in range(n+1):
        c.append(VARINDEX)
        VARINDEX += 1
    
    if n == 1:
        formula.addClause([a[(0)], b[(0)], -c[(0)]])
        formula.addClause([a[(0)], -c[(1)]])
        formula.addClause([b[(0)], -c[(1)]])
        
        # new
        formula.addClause([-a[(0)], c[(0)]])
        formula.addClause([-b[(0)], c[(0)]])
        formula.addClause([c[(1)], -a[(0)], -b[(0)]])
    
    elif n > 1:
        a_even = a[1::2]
        b_even = b[1::2]
        a_odd = a[::2]
        b_odd = b[::2]
        
        d, VARINDEX, formula = sMerge(a_odd, b_odd, k, formula, VARINDEX)
        e, VARINDEX, formula = sMerge(a_even, b_even, k, formula, VARINDEX)
        
        for i in range(n/2):
            formula.addClause([d[(i+1)], e[(i)], -c[(2*i + 1)]])
            formula.addClause([d[(i+1)], -c[(2*i+1 + 1)]])
            formula.addClause([e[(i)], -c[(2*i+1 + 1)]])
            
            #new
            formula.addClause([-d[(i+1)], c[(2*i + 1)]])
            formula.addClause([-e[(i)], c[(2*i + 1)]])
            formula.addClause([-e[(i)], -d[(i+1)], c[(2*i+1 + 1)]])
        
        c = [d[0]] + c[1:]
    
    return c, VARINDEX, formula

def hSort(a, k, formula, VARINDEX):
    
    n = len(a)/2
    c = []
    
    if 2*n == 2:
        c, VARINDEX, formula = hMerge([a[(0)]], [a[(1)]], k, formula, VARINDEX)
    elif 2*n > 2:
        d_1, VARINDEX, formula = hSort(a[:len(a)/2], k, formula, VARINDEX)
        d_2, VARINDEX, formula = hSort(a[len(a)/2:], k, formula, VARINDEX)
        c, VARINDEX, formula = hMerge(d_1, d_2, k, formula, VARINDEX)
    
    return c, VARINDEX, formula

def cardNetwork(a, k, formula, VARINDEX):
    
    n = len(a)
    c = []
    
    if k == n:
        c, VARINDEX, formula = hSort(a, k, formula, VARINDEX)
    elif n > k:
        d_1, VARINDEX, formula = cardNetwork(a[:k], k, formula, VARINDEX)
        d_2, VARINDEX, formula = cardNetwork(a[k:], k, formula, VARINDEX)
        c, VARINDEX, formula = sMerge(d_1, d_2, k, formula, VARINDEX)
    
    return c, VARINDEX, formula

def addCardNetworkBinaryActivation(x, p, formula, VARINDEX, z): # Asin 2011 encoding
    
    n = len(x)
    
    k = p
    
    if math.log(p,2) < math.ceil(math.log(p,2)):
        k = int(math.pow(2,int(math.ceil(math.log(p,2)))))
    
    m = 0
    if n % k > 0:
        m = k - n % k
    elif k > n:
        m = k - n
    
    # Create the vars for dummy inputs bits
    x_dummy = []
    for i in range(m):
        x_dummy.append(VARINDEX)
        formula.addClause([-x_dummy[(i)]])
        VARINDEX += 1
    
    x_extended = x + x_dummy

    c, VARINDEX, formula = cardNetwork(x_extended, k, formula, VARINDEX)
    
    formula.addClause([-z, c[(p-1)]])
    formula.addClause([z, -c[(p-1)]])
    
    return VARINDEX, formula

if __name__ == '__main__':
    import os
    myargs, flags = get_opts()

    encode_hd_maxsat_plan("navigation", "3x3", 4)
    encode_hd_maxsat_plan("navigation", "4x3", 6)
